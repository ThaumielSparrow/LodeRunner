import os, sys
import random

import copy

import time

import re

import pygame

from pygame.locals import K_LSHIFT, K_LCTRL

from newsfeeder import Newsfeeder

from camera import Camera

from map import Map

from inventory import InventoryItem, UpgradePool

from code.tools.eventqueue import EventQueue

from code.controllers.timercontroller import TimerController
from code.controllers.intervalcontroller import IntervalController

from code.extensions.common import UITemplateLoaderExt, HookableExt

from code.tools.xml import XMLParser, XMLNode

from code.game.scripting.script import Script

from code.game.achievement import Achievement

from code.utils.common import offset_rect, intersect, log, log2, logn, xml_encode, xml_decode, create_path, remove_folder, log_msg, ensure_path_exists, resize_image, coalesce

from code.constants.common import TILE_WIDTH, TILE_HEIGHT, CAMERA_SPEED, MAX_PERIMETER_SCROLL_X, MAX_PERIMETER_SCROLL_Y, SCREEN_WIDTH, SCREEN_HEIGHT, QUEST_STATUS_INACTIVE, QUEST_STATUS_IN_PROGRESS, QUEST_STATUS_COMPLETE, QUEST_STATUS_FAILED, SKILL_LIST, ACTIVE_SKILL_LIST, GENUS_PLAYER, GENUS_ENEMY, MODE_EDITOR, MODE_GAME, DIG_RESULT_SUCCESS, COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR, MAX_SKILL_SLOTS, MAX_ENEMY_COUNT, AI_ENEMY_INITIAL_DELAY
from code.constants.common import FADE_CONCENTRIC, FADE_LTR, LAYER_FOREGROUND, LAYER_BACKGROUND, BACKGROUND_MAP_SCALE, BACKGROUND_MAP_PARALLAX_SCALE, SCALE_BY_LAYER, PARALLAX_BY_LAYER, EDITOR_GRID_MINOR_SIZE, EDITOR_GRID_MAJOR_SIZE, EDITOR_MAP_FRAME_THICKNESS, EDITOR_PRIMARY_FRAME_COLOR, EDITOR_SECONDARY_FRAME_COLOR

from code.constants.paths import UNIVERSES_PATH

from code.constants.states import *
from code.constants.death import *

from code.constants.inventory import *

from code.constants.newsfeeder import *
from code.constants.network import *

from code.constants.common import INPUT_DEBUG

# A simple data wrapper
class MapData:

    def __init__(self):#, name, title, x, y, w, h, gold_count):

        self.name = ""
        self.title = ""

        # Release version
        self.version = "0.0"

        # Map class (e.g. overworld, puzzle. etc.).  Useful for rendering worldmap, getting statistics (e.g. total puzzles completed), etc.
        self.class_name = ""

        # Optional "rel" attribute (e.g. which puzzle does this map link to, etc.)
        self.rel = ""

        # Map difficulty (used for puzzle/challenge room popups).  Completely optional, on a technical level, and unused by overworld maps.
        self.difficulty = ""

        self.x = 0
        self.y = 0

        self.width = 0
        self.height = 0

        self.gold_count = 0

        self.layer = LAYER_FOREGROUND


        # This defaults to False; I track (and update) it via the session save file...
        self.visited = False

        # You can't "see" a map on the world map until you visit a map adjacent to it (or the map itself, naturally)
        self.visible = False

        # Same concept here, except we default to "all" gold remaining...
        self.gold_remaining = 0


        # Puzzle / challenge maps will track "completion" (e.g. did we solve the puzzle?)
        self.completed = False

        # Just for fun, we'll track how long the player needed to complete the level.
        # Presently I only render this data for linear level sets.
        self.completion_time = 0


        # Only foreground maps will utilize adjacency data.
        # Adjacency data is used to determine which maps should render
        # (as "inactive" maps for any given "active" level.
        self.adjacent_maps = []

        # Again, only foreground maps will utilize "parallax map" data.
        # This data indicates which parallax maps can render (within the
        # entire parallax-scrolled region) for any given foreground level.
        self.parallax_maps = []


    # Configure
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "class" in options ):
            self.class_name = options["class"]

        if ( "rel" in options ):
            self.rel = options["rel"]

        if ( "title" in options ):
            self.title = options["title"]

        if ( "difficulty" in options ):
            self.difficulty = options["difficulty"]

        if ( "x" in options ):
            self.x = int( options["x"] )

        if ( "y" in options ):
            self.y = int( options["y"] )

        if ( "width" in options ):
            self.width = int( options["width"] )

        if ( "height" in options ):
            self.height = int( options["height"] )

        if ( "gold-count" in options ):
            self.gold_count = int( options["gold-count"] )
            self.gold_remaining = self.gold_count

        if ( "layer" in options ):
            self.layer = int( options["layer"] )

        if ( "completion-time" in options ):
            self.completion_time = int( options["completion-time"] )


        # For chaining
        return self


    # Save state
    def save_state(self):

        # Container
        node = XMLNode("map")

        # Set attributes
        node.set_attributes({
            "name": xml_encode( self.name ),
            "title": xml_encode( self.title ),
            "class": xml_encode( self.class_name ),
            "rel": xml_encode( self.rel ),
            "difficulty": xml_encode( self.difficulty ),
            "x": xml_encode( "%s" % self.x ),
            "y": xml_encode( "%s" % self.y ),
            "width": xml_encode( "%s" % self.width ),
            "height": xml_encode( "%s" % self.height ),
            "gold-count": xml_encode( "%s" % self.gold_count ),
            "layer": xml_encode( "%s" % self.layer ),
            "completion-time": xml_encode( "%s" % self.completion_time )
        })

        # Return state
        return node


    # Load state
    def load_state(self, node):

        log2("**Implement load state for map datum???")
        return


    # Get map name
    def get_name(self):

        # Return
        return self.name


    # Get map title
    def get_title(self):

        # Return
        return self.title


    # Get map class
    def get_class(self):

        # Return
        return self.class_name


    # Check to see if this map has a given class name.
    def has_class(self, class_name):

        # Always return true for wildcard
        if (class_name == "*"):

            # Yes, has class
            return True

        # Otherwise, check class match...
        else:

            # A map can have more than one class.
            for s in self.get_class().split(" "):

                # Check match
                if ( s.strip() == class_name ):

                    # Match
                    return True

            # Does not have the given class
            return False


    # Get the "rel" attribute
    def get_rel(self):

        # Return
        return self.rel


    # Get the map's difficulty level
    def get_difficulty(self):

        return self.difficulty


    # Mark a given map name as adjacent (i.e. within perimeter camera distance) to this map
    def add_adjacent_map(self, name):

        self.adjacent_maps.append(name)


    # Mark a given map name as part of this map's parallax layer
    def add_parallax_map(self, name):

        # No duplicates
        if ( not (name in self.parallax_maps) ):

            # Track
            self.parallax_maps.append(name)


    def reset_world_map_data(self):

        # Reset all worldmap-related data to defaults...
        self.visited = False
        self.visible = False

        self.gold_remaining = self.gold_count

        self.completed = False


    # Mark this map as visible on the world map
    def mark_as_visible(self):

        # Flag
        self.visible = True


    # Mark this map as completed (all gold collected, or whatever)
    def mark_as_completed(self):

        # Flag
        self.completed = True


    # Query completion status
    def is_map_completed(self):

        return self.completed


    # Query visible status
    def is_map_visible(self):

        return self.visible


    # Query visited status
    def is_map_visited(self):

        return self.visited


    # Does the map have gold remaining?
    def has_gold_remaining(self):

        # Check
        return (self.gold_remaining > 0)


# Session variable wrapper.  Key these by variable name in the universe (this object just contains data on the variable).
# Just a hash with some convenience methods.
class SessionVariable:

    # Default variable value
    def __init__(self, default, ignore_reboot = False, ignore_import = False, name = None):

        # Default value
        self.default = default

        # Current value (by default, default, of course)
        self.value = default


        # Most session variables reset on reboot.  Not all do, though.
        self.ignore_reboot = ignore_reboot

        # Most session variables import from save game states.  Not all do, though.
        self.ignore_import = ignore_import


        """ Debugging """
        self.name = name


    # Reset the session variable to its original (default) value
    def reset(self):

        # Default
        self.set_value(self.default)


    # Get the default value
    def get_default(self):

        # Return
        return self.default


    # Get the current value
    def get_value(self):

        # Return
        return self.value


    # Set the current value
    def set_value(self, value):

        if ( self.name == "net.player-limit" ):
            if ( "%s" % value == "4" ):
                logn( 10, "--stacktrace" )

        # Update
        self.value = value


    # Increment the current value
    def increment_value(self, amount):

        # Increment the current value.
        # Only works on numeric values.
        try:

            # Get current value
            current_value = int( self.get_value() )

            # Increment, set
            self.set_value(
                "%d" % ( current_value + int(amount) )
            )

            # Success
            return True

        except:

            # Failure
            return False


# Quest data wrapper
class QuestData(UITemplateLoaderExt):

    def __init__(self, name, title, graphic, xp, description):

        UITemplateLoaderExt.__init__(self)


        # The name helps us query for individual quests (e.g. get-gold)
        self.name = name


        # Each quest has a title (e.g. "Get the gold for me")
        self.title = title

        # Each quest also has a default description (e.g. "Some guy wants you to get his gold for him")
        self.description = description

        # A quest can (i.e. should) have a preview picture.  The preview path is a base name, always found in the universe's "gfx" folder.
        self.graphic = graphic


        # A quest is not active by default; a script must flag it as active...
        self.active = False

        # An active quest will have a status; by default, it will be "inactive."
        # At some point a script will flag it as "complete."
        self.status = QUEST_STATUS_INACTIVE


        # How much XP do you gain for completing this quest?
        self.xp = xp


        # Each quest will have a series of updates; these will provide a sort of play-by-play
        # of the quest's ongoing status / completion.
        self.updates = [] # QuestDataUpdate objects...

        # I try to define updates in chronologic order, but the open-endedness of quest gameplay
        # can lead to unpredictable unlock sequences.  Any time the player activates an update, I'll track it by name in this list.
        self.active_updates_by_name = []
        log2( "Debug message", "INITIALIZING Resetting my active updates" )


    # Save quest state (to an XMLNode)
    def save_memory(self):

        # Create memory node with appropriate attributes
        node = XMLNode("quest").set_attributes({
            "name": xml_encode( self.get_name() ),
            "status": xml_encode( "%s" % self.get_status() )
        })


        # Add an "active updates" tracker
        ref_active_updates = node.add_node(
            XMLNode("active-updates")
        )

        # Add a child node for each known active update
        for name in self.active_updates_by_name:

            # Add Child node
            ref_active_updates.add_node(
                XMLNode("active-update").set_inner_text(name)
            )


        # Return memory node
        return node


    def load_memory(self, ref_quest):

        # Get status
        self.status = int( ref_quest.get_attribute("status") )

        # Active quest?
        self.active = (self.status in (QUEST_STATUS_IN_PROGRESS, QUEST_STATUS_COMPLETE, QUEST_STATUS_FAILED))#(int( ref_quest.get_attribute("active") ) == 1)


        # Reset updates
        for update in self.updates:

            # Reset
            update.reset()


        # Reset known active updates
        self.active_updates_by_name = []
        log2( "Debug message", "Resetting my active updates (%s)" % self.name )

        # Active updates?
        ref_active_updates = ref_quest.find_node_by_tag("active-updates")

        # Validate
        if (ref_active_updates):

            # Loop update name list
            for ref_active_update in ref_active_updates.get_nodes_by_tag("active-update"):

                # Convenience
                name = ref_active_update.innerText

                # Add to known active updates, by name
                self.track_update_by_name(name)

                logn( "universe quests debug", "Loaded quest '%s' update '%s' (active updates:  %s)" % (self.name, name, self.active_updates_by_name) )


        """
        # Check updates...
        update_collection = ref_quest.get_nodes_by_tag("update")

        for ref_update in update_collection:

            # Name of update
            name = ref_update.get_attribute("name")

            # Actual update object
            update = self.get_update_by_name(name)

            # Validate
            if (update):

                update.load_memory(ref_update)
        """


    def get_name(self):

        return self.name


    def get_title(self):

        return self.title


    # Get quest graphic filename
    def get_graphic(self):

        # Return base filename (e.g. quest1.png).  Graphic must exist in the universe's "gfx" folder.
        return self.graphic


    # Get quest description
    def get_description(self):

        return self.description


    # Get a string representing this quest's XP value
    def get_xp_label(self):

        return "(%s xp)" % self.get_xp_value()


    # Get the quest's (raw) status value
    def get_status(self):

        return self.status


    # Get the quest's XP value
    def get_xp_value(self):

        # Return
        return self.xp


    # Get all possible quest updates
    def get_updates(self):

        return self.updates


    # Get currently active (i.e. unlocked / activated) quest updates
    def get_active_updates(self):

        results = []

        # Loop the known sequence of activated update names
        for name in self.active_updates_by_name:

            # Find that update
            update = self.get_update_by_name(name)

            # Validate
            if (update):

                # We don't want to render updates without text.
                # Those updates merely serve to help us in scripting situations (hidden updates).
                if ( len( update.get_description() ) > 0 ):

                    # Add the update to our results
                    #if (update.active):
                    results.append(update)

        return results


    def get_latest_update(self):

        result = None

        for update in self.updates:

            if (update.active):

                result = update

        return result


    # Flag a quest as active, failed, or complete.
    def flag(self, flag_type, control_center, universe):

        # Handle
        localization_controller = control_center.get_localization_controller()


        if (flag_type == "active"):

            # If it's already active, we don't really need (or want) to do anything...
            if (not self.active):

                self.active = True

                # Explicitly mark quest as "in progress"
                self.status = QUEST_STATUS_IN_PROGRESS

                # Post a newsfeeder message
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_QUEST_NEW,
                    "title": localization_controller.get_label("new-quest:header"),
                    "quest": self
                })


        elif (flag_type == "complete"):

            # If it's complete, just leave it be...
            if (self.status != QUEST_STATUS_COMPLETE):

                # ACtive, implicitly
                self.active = True

                self.status = QUEST_STATUS_COMPLETE

                # HACK!
                #universe.get_active_map().get_entity_by_name("player1").increase_xp(350, universe, "+350 XP (Quest Complete!)")

                # Fetch player entity
                player = universe.get_active_map().get_entity_by_name("player1")

                # Validate
                if (player):

                    # Increase the player's XP by this quest's XP worth
                    player.increase_xp(
                        self.get_xp_value(),
                        control_center,
                        universe
                    )

                    # Add a note to the HUD (1-item list)
                    control_center.get_window_controller().get_hud().add_notes([
                        "%s (%d XP)" % ( localization_controller.get_label("quest-complete:lead-in"), self.get_xp_value() )
                    ])


                # Post a newsfeeder update
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_QUEST_COMPLETE,
                    "title": localization_controller.get_label("quest-complete:header"),
                    "quest": self
                })

        elif (flag_type == "failed"):

            # If it's already failed, then do nothing
            if (self.status != QUEST_STATUS_FAILED):

                # ACtive, implicitly
                self.active = True

                # Flag as failed
                self.status = QUEST_STATUS_FAILED

                # Post a newsfeeder update
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_QUEST_FAILED,
                    "title": localization_controller.get_label("quest-failed:header"),
                    "quest": self
                })


    # Track an update by name, adding it to our list of active updates
    def track_update_by_name(self, name):

        # Validate that an update by that name exists
        update = self.get_update_by_name(name)

        # Exists?
        if (update):

            # Don't add duplicates
            if ( not (name in self.active_updates_by_name) ):

                # Track
                self.active_updates_by_name.append(name)


            # Always mark it as active (hard-coded)
            update.active = True


    # Flag a given quest update, by name
    def flag_update_by_name(self, name, flag_type, control_center, universe):

        # Fetch the update
        update = self.get_update_by_name(name)

        # Validate
        if (update):

            # Flag the update.  We'll get True back if it "worked"
            if ( update.flag(flag_type, control_center, universe) ):
            
                # Post a newsfeeder item commemorating the occasion!
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_QUEST_UPDATE,
                    "title": control_center.get_localization_controller().get_label("quest-updated:header"),
                    "quest": self
                })


    # Fetch the status of this quest as either a string or a constant
    def get_status_phrase(self, format = "string"):

        if (not self.active):

            if (format == "string"):
                return "inactive"

            else:
                return 0

        else:

            if (self.status == QUEST_STATUS_INACTIVE):

                if (format == "string"):
                    return "inactive"

                else:
                    return self.status

            elif (self.status == QUEST_STATUS_COMPLETE):

                if (format == "string"):
                    return "complete"

                else:
                    return self.status

            elif (self.status == QUEST_STATUS_FAILED):

                if (format == "string"):
                    return "failed"

                else:
                    return self.status

            else:

                if (format == "string"):
                    return "active"

                else:
                    return self.status


    # Scripts will need this so that they can flag updates as active
    def get_update_by_name(self, name):

        log2( "Debug message:", "quest '%s' searching for '%s' in %s, presumably..." % (self.name, name, self.active_updates_by_name) )

        for update in self.updates:

            if (update.name == name):
                return update

        # Can't find that one
        return None


# QuestData update wrapper
class QuestDataUpdate(UITemplateLoaderExt):

    def __init__(self, quest_name, quest_title, name, description):

        UITemplateLoaderExt.__init__(self)


        # Let's remember the name of the parent quest
        self.parent_quest_name = quest_name

        # Parent quest title as well
        self.parent_quest_title = quest_title


        # The "name" of an update only helps us to query it by name (e.g. update1)
        self.name = name

        # The description provides the user-visible data (e.g. "I found the gold; I should take it back to complete the quest.")
        self.description = description


        # By default, the update is inactive; a script must flag it as enabled before the player can see it.
        self.active = False


    # Reset an update
    def reset(self):

        # Right now, we just want to make sure to set it in inactive...
        self.active = False


    def load_memory(self, ref_update):

        # Is the update active?
        self.active = (int( ref_update.get_attribute("active") ) == 1)


    # Get update name
    def get_name(self):

        return self.name


    # Get update description
    def get_description(self):

        return self.description


    # Check to see if the update is active
    def is_active(self):

        return self.active


    def get_status_phrase(self, format = "string"):

        if (not self.active):

            if (format == "string"):
                return "inactive"

            else:
                return 0

        else:

            if (format == "string"):
                return "active"

            else:
                return 1


    def flag(self, flag_type, control_center, universe):

        if (flag_type == "active"):

            # Don't do anything if this update is already active
            if (not self.active):

                # Flag as active
                self.active = True

                # I guess I'm going to reach back into the universe, find the parent quest,
                # and add this upate's name to the "active updates by name" list.  Kind of hacky, but hey.  It works.
                universe.get_quest_by_name(self.parent_quest_name).track_update_by_name(self.name)


                # Return success
                return True


        # Return that we did nothing
        return False


# A wrapper to store statistics for an individual skill, including duration, recharge time, and modifier data
class SkillStatsItem:

    def __init__(self):

        # Minimum character level
        self.min_character_level = 1

        # Cost (in skill points)
        self.cost = 1 # Default to 1


        # How long does the skill last?  (measured in frames)
        self.duration = 0

        # Recharge time?  (measured in frames)
        self.recharge_time = 0


        # A skill can have "modifiders."  When the player activates a skill,
        # it will consult these modifiers to determine whether to apply certain
        # effects (such as "mega bomb has a +5 blast radius") to the skill.
        self.modifiers = {
            "timer-drain": 1,                       # Presets global to all skills unless
            "timre-drain-while-motionless": 1       # explicitly overridden (e.g. invisibility level 3)
        }


        # Skill description (for billboards, maybe manuals)
        self.description = ""

        # Skill manual (for equip skills screen)
        self.manual = ""


    # Load in metrics from a given node
    def load_from_node(self, node):

        # Check for minimum character level
        ref_min_character_level = node.get_first_node_by_tag("min-character-level")

        if (ref_min_character_level):

            self.min_character_level = int( ref_min_character_level.innerText )

        # Check for cost (in skill points)
        ref_cost = node.get_first_node_by_tag("cost")

        if (ref_cost):

            self.cost = int( ref_cost.innerText )


        # Load in duration
        ref_duration = node.get_first_node_by_tag("duration")

        if (ref_duration):

            (measure, value) = (
                ref_duration.get_attribute("measure"),
                ref_duration.innerText
            )

            # Calculate duration.  It's always measured in frames, so we'll make it an int.
            self.duration = int( self.convert_value_by_measure(value, measure) )


        # Load in recharge time
        ref_recharge = node.get_first_node_by_tag("recharge")

        if (ref_recharge):

            (measure, value) = (
                ref_recharge.get_attribute("measure"),
                ref_recharge.innerText
            )

            # Calculate recharge time.  It's also always measrued in frames, so we'll make it an int as well.
            self.recharge_time = int( self.convert_value_by_measure(value, measure) )


        # Check for a modifiers collection
        ref_modifiers_list = node.get_first_node_by_tag("modifiers")

        if (ref_modifiers_list):

            # Grab all modifiers
            modifier_collection = ref_modifiers_list.get_nodes_by_tag("modifier")

            # Check each one...
            for ref_modifier in modifier_collection:

                # Here, we'll convert the value to a float.  Values are always numerical.  (Or, they'd better be!)
                (key, value) = (
                    ref_modifier.get_attribute("name"),
                    float( ref_modifier.get_attribute("value") )
                )

                # Store in modifiers hash
                self.modifiers[key] = value


        # Load description
        ref_description = node.get_first_node_by_tag("description")

        if (ref_description):

            self.description = ref_description.innerText


        # Load manual
        ref_manual = node.get_first_node_by_tag("manual")

        if (ref_manual):

            self.manual = ref_manual.innerText


    def convert_value_by_measure(self, value, measure):

        if (measure == "seconds"):

            return (60 * float(value))

        else:

            return float(value)


    def get_min_character_level(self):

        return self.min_character_level


    def get_cost(self):

        return self.cost


    def get_duration(self):

        return self.duration


    def get_recharge_time(self):

        return self.recharge_time


    def get_modifier_by_name(self, name):

        # Validate
        if (name in self.modifiers):

            return self.modifiers[name]

        # I guess we'll just return 0 by default, what the heck!
        else:

            return 0 # This should really never happen...


    def get_description(self):

        return self.description


    def get_manual(self):

        return self.manual


# A wrapper to store statistics for each skill in the game.
# These can theoretically vary from universe to universe...
class SkillStats:

    def __init__(self):

        # We'll keep the skill data in a hash.  Ultimately, each of these hashes
        # will contain a separate hash for each possible skill level...
        self.stats_by_skill = {}


    # Load in any or all skill statistical data from an xml node
    def load_from_node(self, node):

        # Which skill is this node describing?
        skill = node.tag_type

        # Validate that this is a real skill
        if (skill in SKILL_LIST):

            # Fetch all "stats" nodes... one per possible skill level
            stats_collection = node.get_nodes_by_tag("data")

            for ref_stats in stats_collection:

                # Which tier is this for?
                tier = ref_stats.get_attribute("tier")

                # Create a hash entry for this skill/tier, adding a SkillStatsItem
                # based on the data within ref_stats...
                if (not (skill in self.stats_by_skill)):

                    # A separate key / value for each skill level
                    self.stats_by_skill[skill] = {}


                # Add the new SkillStatsItem container
                self.stats_by_skill[skill][tier] = SkillStatsItem()

                # Load in the given metrics
                self.stats_by_skill[skill][tier].load_from_node(
                    ref_stats.get_first_node_by_tag("attributes")
                )


    def get_skill_stats_by_level(self, skill, level):

        # We hash everything by a string
        level = "%s" % level # Cast ints to string

        # Validate
        if (skill in self.stats_by_skill):

            # More validation
            if (level in self.stats_by_skill[skill]):

                return self.stats_by_skill[skill][level]


        # I guess we couldn't find stats for that skill/level
        return None


    def get_skill_max_level(self, skill):

        # Validate
        if (skill in self.stats_by_skill):

            # More validation
            if ( len(self.stats_by_skill[skill]) > 0 ):

                # We only care about actual numeric skill levels (not "locked" or "max")
                return max( int(o) for o in self.stats_by_skill[skill].keys() if re.sub("[^0-9]", "", o) == o )


        # Probably shouldn't ever hit this...
        return 0


# Universe Controller
class Universe(HookableExt):

    def __init__(self, name, game_mode, control_center, is_new = False, meta_only = False):

        HookableExt.__init__(self)


        # Name of the universe
        self.name = name

        # Readable title of the universe
        self.title = "Untitled Universe"


        # Each universe object will load in collision values, ordered in a
        # flat list by tile index.  Some universes will use custom tilesheets
        # with their own distinct collision definitions.
        self.collision_values_by_tile_index = []


        # A universe can use the default tilesheet, or it can use a custom-specified spritesheet (in universe metadata).
        # We'll use this variable to track the custom tilesheet's filepath.
        self.custom_tilesheet_filepath = None

        # If we want to use a custom tilesheet, we'll also want to keep a handle to it (after we add it to the gfx controller)
        self.custom_tilesheet = None


        # Universe type (story, linear, etc.).  Defaults to linear.
        self.type = "linear"


        # Min players (should be defined by meta file)
        self.min_players = 1

        # Max players (meta file)
        self.max_players = 1


        # Unsaved universe?
        self.saved = False


        # For level editor (can't create duplicate names, etc.)
        self.error = None


        # Track this Universe's achievements in a simple list
        self.achievements = []

        # When we first execute a hook, we'll make a quick cache of any achievement that responds to that hook (a lookup table, of sorts).
        # Each time we execute that same hook thereafter, we will consult this cache.
        self.achievement_hook_cache = {}


        # Track camera location
        self.camera = Camera(0, 0)

        # When an intermap transition occurs, we'll load the new maps we need and such.
        # Flagging this will cause us to discard offscreen (non-adjacent) map objects
        # whenever the camera reaches its target destination. 
        self.discard_offscreen_maps_on_camera_shift_completion = False


        # As we move from level to level, we'll update the parallax layer prerender for
        # each new map once the camera settles in.
        self.prerender_status = PRERENDER_STATUS_PENDING # Default to pending as the game begins

        # The prerender is larger than the app display, and we try to center it each time we
        # compute it.  As such, we need to track how much offset we used to achieve the centering effect.
        self.prerender_offsets = (0, 0)


        # (?) (redundant?) Invalidate the splash controller to fetch fresh background data
        control_center.get_splash_controller().invalidate()


        # We can pause the universe to stop game action.  We'll do this during certain menus, and also during dialogue sequences.
        # We use a counter so that if we pause the game during a dialogue sequence (i.e. already paused), we don't incorrectly
        # resume the game when we dismiss the pause menu.
        # Note that some menus (e.g. netplay pause menu) will NOT actually pause the universe.
        self.pause_count = 0


        # During network play, we may want to lock map processing pending network activity...
        self.locks = {}

        # Track overall lock status
        self.lock_count = 0

        self.under_soft_lock = False
        self.under_hard_lock = False


        # Track data for all maps
        self.map_data = {
            LAYER_BACKGROUND: {},
            LAYER_FOREGROUND: {}
        }

        # Each map will track which maps are near it (within perimeter scroll view)
        self.adjacency_data = {
            LAYER_BACKGROUND: {},
            LAYER_FOREGROUND: {}
        }


        # Maps on the foreground layer must track which background (parallax) maps
        # might render while playing on the foreground map.
        self.parallax_data = {
            LAYER_BACKGROUND: {}, # Unused, just trying to make the code parallel
            LAYER_FOREGROUND: {}  # Computed on universe load
        }


        # **Track active map name, whatever.  Foreground only.  Can't play on background map.  Delete this sometime, I should be using .get_active_map exclusively
        self.active_map_name = None


        # Sometimes we might want to set a universe to ignore memory data, instead of
        # flagging individual maps.  I use this most famously in the main menu GIF widgets.
        self.ignore_map_memory_files = False


        # The universe always* has an active map.  At times, though, we'll want to
        # "push" some other map on "top" of it, so that the call to get_active_map() returns the
        # pushed map instead of the "real" active map (e.g. when running onbirth scripts for adjacent maps).
        self.pushed_map_stack = []


        # Default primary map (must be a foreground map).  Remember it for level editor purposes.
        self.primary_map_name = ""

        # Visible maps cache
        self.visible_maps = {
            LAYER_BACKGROUND: {}, # I don't think we'll ever populate this (we'll prerender / cache parallax maps), but let's just put it here for code parallelism
            LAYER_FOREGROUND: {}
        }


        # A universe might contain "global" scripts, scripts that do not apply to a single
        # map.  Individual maps / dialogue sequences can call these global scripts, and various
        # in-game events (e.g. level up) can also call one of these scripts.
        self.scripts = {}

        # Compile on-the-fly, as needed...
        self.compiled_scripts = {}


        # 99% of the time, NPCs will store their own conversation (dialogue) data, loaded from the level files.
        # Occasionally, though, an NPC will import a "global" conversation that does not directly apply to any individual NPC.
        # Quite clearly, we use these for the stray "common" conversation that might occur during the game, where different people say the same exact thing(s).
        # NOte that we keep references to the xml nodes we find; NPCs import conversations by parsing xml nodes.
        self.conversation_nodes = {}


        # Sometimes we'll display an overworld menu (e.g. for "game over" screen)
        self.overworld_menu = None


        # Current alpha data
        self.alpha_controller = IntervalController(
            interval = 1.0,
            target = 1.0,
            speed_in = 0.015,
            speed_out = 0.020
        )

        # Current fade style
        self.fade_style = FADE_LTR


        # Set up a timer controller
        self.timer_controller = TimerController()


        # Let's give the universe itself an hslide controller, so that we can
        # slide it in / out of view as we transition from / to the main menu.
        self.hslide_controller = IntervalController(
            interval = SCREEN_WIDTH,
            target = 0,
            speed_in = 15,
            speed_out = 15,
            integer_based = 1
        )


        # By default, assume we level up once for every 500XP gained, up to level 25.
        # The universe's metafile can (and probably should) overwrite this.
        self.level_xp_requirements = [
            {
                "level": i,
                "xp":    (i * 500)
            }
            for i in range( 1, 25 + 1 )
        ]


        # Stats for each skill/level
        self.skill_stats = SkillStats()


        # Quest data collection
        self.quests = []

        # We'll keep a list of the order in which we acquire quests, so that we can render them order of acquisition.
        # This list tracks quests by quest name.  "Active" can indicate in-progress, complete, or failed.
        self.active_quests_by_name = []


        # Items that exist within the universe
        self.items = []

        # Upgrade pools
        self.upgrade_pools = []


        # A universal set of items that the player has acquired during the game
        self.acquired_inventory = []

        # A universal set of items that the player has equipped
        self.equipped_inventory = []


        # To help optimize calculations relating to the player's equipped items,
        # we'll hold a universal "item result" cache that saves various calculations (e.g. player speed, enemy speed, etc.)
        # We won't use this for every single item attribute result, not necessarily anyway.
        self.item_attribute_result_cache = {}


        # Track game session.  Some values always exist (e.g. abilities), whereas
        # others are defined by a universe's configuration file.

        # Note:  This is populated (default values, at least) within reset()
        self.session = {}

        # Fresh start
        self.reset()


        # As we play through the game, we will make imprints upon the world, various
        # "historical events" such as killing NPCs, getting one-time discounts, special items,
        # stuff like that.  We will log all of these historial events,
        # keyed by type, each key holding a list of event ids.
        self.historical_records = {
            "game": [                   # We can add any key we want via script.  By default, just this one type exists.
                "begin-game"            # We can add in any string value.  It can be a key, a phrase, whatever.
            ]
        }


        # Validate the name first if it's new...
        if (is_new):

            name = name.strip()

            # If a universe with this name already exists, return False...
            if (os.path.exists( os.path.join("universes", "%s.xml" % name) )):

                self.error = "Already exists"

            elif (name == ""):

                self.error = "Name required"

        # Loaded universes (previously existing) are thus already saved under their previous name...
        else:

            # If we're in game mode, we should clear any active map history data
            if (game_mode == MODE_GAME):

                # Before we officially begin the game, clear out any "active" history data.
                # We want a completely fresh start for the new game.
                active_path = os.path.join( self.get_working_save_data_path(), "active" )

                # Remove the folder if it exists
                if ( os.path.exists(active_path) ):

                    # Remove folder
                    remove_folder(active_path)


            # Now we can load the universe's data
            self.load(game_mode, control_center, meta_only = meta_only)

            # For editor purposes
            self.saved = True


            # Get current language preference
            language = control_center.get_localization_controller().get_language()

            # Calculate path to this universe's localization data
            path = os.path.join( UNIVERSES_PATH, self.name, "localization", "%s.xml" % language )

            # Validate path
            if ( os.path.exists(path) ):

                # Load universe's relative localization data
                control_center.get_localization_controller().load(path)


    def reset(self):

        self.error = None

        for layer in (LAYER_BACKGROUND, LAYER_FOREGROUND):

            self.map_data[layer].clear()

            self.adjacency_data[layer].clear()

            # Empty the visible maps cache
            self.visible_maps[layer] = {}


        self.active_map_name = None

        # Default primary map
        self.primary_map_name = ""



        # Reset skill stats
        self.skill_stats = SkillStats()

        # Clear quests
        self.quests = []

        # Clear items
        self.items = []

        # Track game session.  Some values always exist (e.g. abilities), whereas
        # others are defined by a universe's configuration file.
        self.session.clear()

        self.session = {
            "app.load-from-folder": SessionVariable(""),

            "app.active-map-name": SessionVariable("x"),
            "app.transition.from.map": SessionVariable(""),
            "app.transition.from.waypoint": SessionVariable(""),
            "app.transition.from.player-x": SessionVariable(""),
            "app.transition.from.player-y": SessionVariable(""),
            "app.transition.to.map": SessionVariable(""),
            "app.transition.to.waypoint": SessionVariable(""),

            "app.quests.inactive": SessionVariable("inactive"),
            "app.quests.active": SessionVariable("active"),
            "app.quests.complete": SessionVariable("complete"),

            "app.rebuild-response-menu": SessionVariable("0"),

            "app.max-enemy-count": SessionVariable( "%d" % MAX_ENEMY_COUNT ),

            "algebra.x": SessionVariable("0"),
            "algebra.y": SessionVariable("0"),
            "algebra.z": SessionVariable("0"),

            "core.keyboard.value": SessionVariable(""),
            "core.player.entered-name": SessionVariable("no"),

            "core.overworld-title": SessionVariable("Overworld"),

            "core.is-gif": SessionVariable("0"),

            "core.received-player-id": SessionVariable("0", ignore_import = True),

            "core.generated-splash": SessionVariable("0"),

            "core.puzzle-room-virgin": SessionVariable("1"),

            "core.is-dummy-session": SessionVariable("0"),

            "core.handled-local-death": SessionVariable("0", ignore_reboot = True, ignore_import = True),

            "core.minimap.can-travel": SessionVariable("no"),   # When "no," disable travel button on world map.  Set to "yes" when appropriate via script (e.g. when visiting 2nd town in a story mode game).

            "core.x": SessionVariable("0"),
            "core.y": SessionVariable("0"),
            "core.z": SessionVariable("0"),

            "core.constants.death-by-tile-fill": SessionVariable(""),
            "core.constants.death-by-enemy": SessionVariable(""),
            "core.constants.death-by-planar-shift": SessionVariable(""),
            "core.constants.death-by-out-of-bounds": SessionVariable(""),
            "core.constants.death-by-deadly-tile": SessionVariable(""),
            "core.constants.death-by-bomb": SessionVariable(""),
            "core.constants.death-by-vaporization": SessionVariable(""),

            "core.time.played": SessionVariable("0"),

            "core.time": SessionVariable("0"),
            "core.chapter": SessionVariable("1"),

            "core.player-id": SessionVariable("1", ignore_import = True),

            "core.player1.name": SessionVariable("HERO"),
            "core.player1.colors": SessionVariable(""),#SessionVariable("primary=225,25,25;secondary=225,225,225"),

            "net.online": SessionVariable("0", ignore_import = True),
            "net.session.id": SessionVariable("0", ignore_import = True),

            "net.player-limit": SessionVariable("4", ignore_import = True, name = "net.player-limit"),
            "net.password": SessionVariable("", ignore_import = True),
            "net.port": SessionVariable("", ignore_import = True),

            "net.rebuild-intro-menu": SessionVariable("0", ignore_import = True),
            "net.rebuild-intro-menu:curtailed-count": SessionVariable("0", ignore_import = True),

            "net.countdown-in-progress": SessionVariable("0", ignore_import = True),
            "net.game-in-progress": SessionVariable("0", ignore_import = True),

            "net.level.complete": SessionVariable("0", ignore_import = True),
            "net.level.failed": SessionVariable("0", ignore_import = True),

            "net.votes-to-skip": SessionVariable("0", ignore_import = True),
            "net.already-voted-to-skip": SessionVariable("0", ignore_import = True),

            "net.transition.target": SessionVariable("", ignore_import = True),

            "net.player1.joined": SessionVariable("1", ignore_import = True),
            "net.player2.joined": SessionVariable("0", ignore_import = True),
            "net.player3.joined": SessionVariable("0", ignore_import = True),
            "net.player4.joined": SessionVariable("0", ignore_import = True),

            "net.player1.received-nick": SessionVariable("0", ignore_import = True),
            "net.player2.received-nick": SessionVariable("0", ignore_import = True),
            "net.player3.received-nick": SessionVariable("0", ignore_import = True),
            "net.player4.received-nick": SessionVariable("0", ignore_import = True),

            "net.player1.nick": SessionVariable("Player 1", ignore_import = True),
            "net.player2.nick": SessionVariable("Player 2", ignore_import = True),
            "net.player3.nick": SessionVariable("Player 3", ignore_import = True),
            "net.player4.nick": SessionVariable("Player 4", ignore_import = True),

            "net.player1.ready": SessionVariable("0", ignore_import = True),
            "net.player2.ready": SessionVariable("0", ignore_import = True),
            "net.player3.ready": SessionVariable("0", ignore_import = True),
            "net.player4.ready": SessionVariable("0", ignore_import = True),

            "net.player1.avatar.colors": SessionVariable("primary=225,25,25;secondary=225,225,225", ignore_import = True),
            "net.player2.avatar.colors": SessionVariable("primary=25,225,25;secondary=225,225,225", ignore_import = True),
            "net.player3.avatar.colors": SessionVariable("primary=25,25,225;secondary=225,225,225", ignore_import = True),
            "net.player4.avatar.colors": SessionVariable("primary=225,25,225;secondary=225,225,225", ignore_import = True),

            "core.player1.x": SessionVariable("0"),
            "core.player1.y": SessionVariable("0"),

            "core.player1.cause-of-death": SessionVariable(""),

            "core.player1.inventory-size": SessionVariable("2"),

            "core.last-safe-zone.map": SessionVariable(""),
            "core.last-safe-zone.title": SessionVariable(""),

            "core.xp.bonus.completionist": SessionVariable("125"),     # Bonus for collecting all of the gold on an overworld map
            "core.xp.bonus.pacifist": SessionVariable("50"),            # Bonus for doing so without killing a bad guy
            "core.xp.bonus.no-bombs": SessionVariable("25"),            # Bonus for doing so without using a single bomb

            "core.xp-bar.percent-old": SessionVariable("0.0"),
            "core.xp-bar.percent-new": SessionVariable("0.0"),
            "core.xp-bar.timer": SessionVariable("0"),
            "core.xp-bar.timer-max": SessionVariable("0"),
            "core.xp-bar.total-earned": SessionVariable("0"),
            "core.xp-bar.message": SessionVariable(""),

            "core.worldmap.view": SessionVariable("gold"),
            "core.worldmap.zoom": SessionVariable("1.0"),

            "core.dialogue-response": SessionVariable(""),
            "core.login-succeeded": SessionVariable("no"),

            "core.gold.found": SessionVariable("0"),
            "core.gold.wallet": SessionVariable("0"),
            "core.gold.wallet:visible": SessionVariable("0"),   # If the player gains multiple gold pieces, we'll slowly tick the HUD counter upward (while updating the actual wallet value immediately)

            "core.bombs.count": SessionVariable("0"),

            "core.challenge.wave": SessionVariable("0"),   # Controlled by door trigger scripts (i.e. script sets it to 1 when using a door into a challenge room)

            "core.player1.level": SessionVariable("1"),
            "core.player1.xp": SessionVariable("0"),
            "core.player1.skill-points": SessionVariable("0"),

            "core.player1.skill1": SessionVariable(""),
            "core.player1.skill2": SessionVariable(""),

            "core.player1.skill1:changed": SessionVariable("0"),
            "core.player1.skill2:changed": SessionVariable("0"),

            "core.skills.invisibility:power-drain": SessionVariable(""),
            "core.skills.invisibility:power-drain-while-motionless": SessionVariable(""),

            "stats.bombs-used": SessionVariable("0"),
            "stats.enemies-killed": SessionVariable("0"),
            "stats.digs": SessionVariable("0"),
            "stats.items-bought": SessionVariable("0"),
            "stats.skills-unlocked": SessionVariable("0"),
            "stats.gold-spent": SessionVariable("0")
        }

        # Add a default session entry for each skill
        for skill in SKILL_LIST:

            self.session["core.skills.%s" % skill] = SessionVariable("0")

            self.session["core.skills.%s:lastused" % skill] = SessionVariable("0")
            self.session["core.skills.%s:locked" % skill] = SessionVariable("0")

            # For how long will the skill last?
            self.session["core.skills.%s:timer" % skill] = SessionVariable("0")
            self.session["core.skills.%s:timer-max" % skill] = SessionVariable("0")

            # Timer drain statistics
            self.session["core.skills.%s:timer-drain" % skill] = SessionVariable("0")
            self.session["core.skills.%s:timer-drain-while-motionless" % skill] = SessionVariable("0")

            # After use, active skills will have a recharge period, typically...
            self.session["core.skills.%s:recharge-remaining" % skill] = SessionVariable("0")
            self.session["core.skills.%s:recharge-potential" % skill] = SessionVariable("0")


        # Special parameters for the remote bomb skill
        self.session["core.skills.remote-bomb:bombs-remaining"] = SessionVariable("0")


        # Temporary hack?
        #for skill in ("sprint", "personal-shield", "remote-bomb"):
        #    self.session["core.skills.%s" % skill]["value"] = "0"

        # Ensure we're using default, reset inventory, etc.
        self.reboot()


    def reboot(self):

        # Clear each layer's visible map data
        for layer in self.visible_maps:

            # Clear
            self.visible_maps[layer].clear()


        # Reset world map data
        self.reset_world_map_data()


        # Clear our list of known quest names
        self.active_quests_by_name = []


        # No item acquired
        self.acquired_inventory = []

        # No item equipped
        self.equipped_inventory = []


        # Clear historical records for the current session
        self.historical_records = {}


        # Reset all session variables to default
        for key in self.session:

            # See if we should ignore the reboot for this session variable
            if (not self.session[key].ignore_reboot):

                # Reset variable to its default
                self.session[key].reset()


        # If we're rebooting the universe, then we haven't handled local player death yet.
        # We're starting fresh.
        self.set_session_variable("core.handled-local-death", "0")


    # Import a session
    def import_session(self, values):

        log2("importing session data...")

        # Now loop through the given session variables
        # Reset all session variables to default
        for key in values:

            # If this isn't a default session variable (i.e. it's created by a script in a universe),
            # let's implicitly create it now.
            if ( not (key in self.session) ):

                # Create with no default value (default to 0?)
                self.session[key] = SessionVariable("0")


            # Safe to import?
            if (not self.session[key].ignore_import):

                self.get_session_variable(key).set_value(values[key])


    # Import default collision values
    def import_default_collision_values(self):

        # Load in xml
        root = XMLParser().create_node_from_file(
            os.path.join("data", "xml", "default.collision.values.xml")
        )

        # Validate
        if (root):

            # Check for data node
            ref_collision_values = root.find_node_by_tag("collision-values")

            # Validate
            if (ref_collision_values):

                # Import default collision values
                self.import_collision_values_from_node(ref_collision_values)


    # Import collision values from a given xml node
    def import_collision_values_from_node(self, node):

        # Reset any existing collision value
        self.collision_values_by_tile_index = []

        # Get the inner text.  Strip leading/trailing whitespace,
        # then replace all new lines with commas to create a flat list.
        data = node.get_inner_text().strip().replace("\r", "").replace("\n", ",")

        # Loop through all comma-separated values
        for value in data.split(","):

            # Add integer value to flat list
            self.collision_values_by_tile_index.append( int(value.strip()) )


    # Get a handle to this universe object's collision values
    def get_collision_values(self):

        # Return handle
        return self.collision_values_by_tile_index


    # Load universe data from file...
    def load(self, game_mode, control_center, meta_only = False):

        # Reset universe data
        self.reset()


        # Check for meta data (title, etc.)
        path = os.path.join( UNIVERSES_PATH, self.name, "meta.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create a node from the meta file data
            ref = XMLParser().create_node_from_file(path).find_node_by_tag("metadata")


            # Check for version tag
            ref_version = ref.find_node_by_tag("version")

            # Validate
            if (ref_version):

                # Read version
                self.version = ref_version.innerText


            # Check for params tag
            ref_params = ref.find_node_by_tag("params")

            # Validate
            if (ref_params):

                # Grab the universe's human-readable title
                self.title = ref_params.find_node_by_id("title").innerText


                # Check for min/max player params
                (ref_min_players, ref_max_players) = (
                    ref_params.find_node_by_id("min-players"),
                    ref_params.find_node_by_id("max-players")
                )

                # Validate
                if ( (ref_min_players != None and ref_max_players != None) ):

                    # Update
                    self.min_players = int( ref_min_players.innerText )
                    self.max_players = int( ref_max_players.innerText )


            # Look for character level/xp definitions
            ref_character_levels = ref.find_node_by_tag("character-levels")

            # Validate
            if (ref_character_levels):

                # Clear all existing data
                self.level_xp_requirements = []

                # Loop defined character levels
                for ref_character_level in ref_character_levels.get_nodes_by_tag("character-level"):

                    # Add level data
                    self.level_xp_requirements.append({
                        "level": int( xml_decode( ref_character_level.find_node_by_tag("level").innerText ) ),
                        "xp":    int( xml_decode( ref_character_level.find_node_by_tag("xp").innerText ) )
                    })


            # Check for universe type node
            ref_type = ref.find_node_by_tag("params").find_node_by_id("type")

            # Validate
            if (ref_type):

                # Always track type
                self.type = ref_type.innerText


                # If this is a linear universe, then let's turn on the ignore map memory flag
                if (ref_type.innerText == "linear"):

                    # Ignore map memory, as we don't travel from map to map in an overworld
                    self.ignore_map_memory_files = True


            # Check for custom spritesheet filepath node
            ref_custom_tilesheet = ref.find_node_by_tag("tilesheet")

            # Validate (we might not specify a custom spritesheet, after all)
            if (ref_custom_tilesheet):

                # Check for filename.
                ref_filename = ref_custom_tilesheet.find_node_by_tag("filename")

                # Validate
                if (ref_filename):

                    # We must find the specified tilesheet file within this universe's gfx folder.
                    filepath = os.path.join(
                        UNIVERSES_PATH, self.get_name(), "gfx", ref_filename.innerText
                    )

                    # Validate that the file exists!
                    if ( os.path.exists(filepath) ):

                        # Generic a key for the spritesheet name, based on this universe's name
                        key = "%s" % self.get_name() # Okay, we're just using the universe's name, whatever...

                        # Add the custom spritesheet
                        control_center.get_window_controller().get_gfx_controller().add_spritesheet_with_name(
                            key, filepath, TILE_WIDTH, TILE_HEIGHT, first_pixel_transparent = False             # We'll use purple as transparent (#ff00ff)
                        )

                        # Save a handle to that tilesheet
                        self.custom_tilesheet = control_center.get_window_controller().get_gfx_controller().get_spritesheet_by_name(key)


                # Check for collision values
                ref_collision_values = ref_custom_tilesheet.find_node_by_tag("collision-values")

                # Validate
                if (ref_collision_values):

                    # Import collision values now
                    self.import_collision_values_from_node(ref_collision_values)


            # If at this point (after checking for optional custom tilesheet)
            # we haven't loaded in any collision values, we'll fall back to the
            # default collision values (presumably we're using the default tilesheet).
            if ( len(self.collision_values_by_tile_index) == 0 ):

                # Import default collision values
                self.import_default_collision_values()


        # If no meta.xml file exists (non-playable universe),
        # we should at least import default collision values.
        else:
            self.import_default_collision_values()


        # Check for map data
        path = os.path.join( UNIVERSES_PATH, self.name, "maps.xml" )

        # Although we're not going to activate the primary map right away (we still want to load other universe data first,
        # we'll want to remember it for future use.
        primary_map_name = None

        # Validate
        if ( os.path.exists(path) ):

            # Read in essential universe data (maps, primary map) into a wrapper node
            node = XMLParser().create_node_from_file(path)


            # Get all maps in the universe
            ref_maps = node.get_first_node_by_tag("maps")

            # Validate
            if (ref_maps):

                # Check for a primary map definition
                ref_primary_map = ref_maps.find_node_by_tag("primary-map")

                # Validate
                if (ref_primary_map):

                    # Remember it for future use
                    primary_map_name = xml_decode( ref_primary_map.get_attribute("name") )


                # Find foreground and background maps
                (ref_background, ref_foreground) = (
                    ref_maps.get_first_node_by_tag("background"),
                    ref_maps.get_first_node_by_tag("foreground")
                )


                # Background
                if (ref_background):

                    # Find all maps
                    map_collection = ref_background.get_nodes_by_tag("map")

                    # Loop
                    for ref_map in map_collection:

                        map_name = "%s" % ref_map.get_attribute("name")
                        map_title = "%s" % ref_map.get_attribute("title")

                        options = {
                            "name": xml_decode( map_name ),
                            "title": xml_decode( map_title )
                        }

                        # Check for other common attributes
                        for prop in ("class", "rel", "title", "difficulty", "x", "y", "width", "height", "gold-count", "layer"):

                            if ( ref_map.has_attribute(prop) ):
                                options[prop] = xml_decode( ref_map.get_attribute(prop) )


                        # Track general map data
                        self.map_data[LAYER_BACKGROUND][map_name] = MapData().configure(options)


                # Foreground
                if (ref_foreground):

                    # Find all maps
                    map_collection = ref_foreground.get_nodes_by_tag("map")

                    # Loop
                    for ref_map in map_collection:

                        map_name = "%s" % ref_map.get_attribute("name")
                        map_title = "%s" % ref_map.get_attribute("title")

                        options = {
                            "name": xml_decode( map_name ),
                            "title": xml_decode( map_title )
                        }

                        # Check for other common attributes
                        for prop in ("class", "rel", "title", "difficulty", "x", "y", "width", "height", "gold-count", "layer"):

                            if ( ref_map.has_attribute(prop) ):
                                options[prop] = xml_decode( ref_map.get_attribute(prop) )


                        # Track general map data
                        self.map_data[LAYER_FOREGROUND][map_name] = MapData().configure(options)


            # Now that we've loaded in all of the maps, let's take a moment to calculate each individual (foreground) map's adjacency data...
            self.calculate_adjacency_data_on_layer(LAYER_FOREGROUND)

            # Calculate the foreground layer's parallax data
            self.calculate_parallax_data()


        # Check for quest data
        path = os.path.join( UNIVERSES_PATH, self.name, "quests.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Import file contents into a wrapper node, then find the hard quest data
            ref = XMLParser().create_node_from_file(path).find_node_by_tag("quests")

            # Validate
            if (ref):

                # Loop through each quest this universe contains
                for ref_quest in ref.get_nodes_by_tag("quest"):

                    # Get the name
                    quest_name = "%s" % ref_quest.get_attribute("name")


                    # Defaults
                    (quest_title, quest_description, quest_graphic) = ("", "", "")


                    # Title
                    quest_title = "%s" % ref_quest.get_attribute("title")

                    # Try to find a quest graphic filename (e.g. quest1.png, a base filename)
                    if ( ref_quest.has_attribute("graphic") ):

                        # Overwrite
                        quest_graphic = ref_quest.get_attribute("graphic")


                    # See if we can get a description...
                    quest_description = "No description available."

                    ref_description = ref_quest.get_nodes_by_tag("description")

                    if (len(ref_description) > 0):
                        quest_description = ref_description[0].innerText.strip()


                    # Assume
                    quest_xp = 250 # Hard-coded default

                    # Check for a given xp value
                    if ( ref_quest.has_attribute("xp") ):

                        # Update
                        quest_xp = int( ref_quest.get_attribute("xp") )


                    # Instantiate a QuestData object
                    quest = QuestData(quest_name, quest_title, quest_graphic, quest_xp, quest_description)


                    # Query any update related to this quest...
                    update_collection = ref_quest.get_nodes_by_tag("update")

                    for ref_update in update_collection:

                        update_name = "%s" % ref_update.get_attribute("name")
                        update_description = ref_update.innerText.strip()

                        # Append a QuestDataUpdate to the quest...
                        quest.updates.append( QuestDataUpdate(quest_name, quest_title, update_name, update_description) )


                    # Lastly, add the quest to the collection...
                    self.quests.append(quest)


        """ Quick load check """
        # If we only care about this universe's metadata (e.g. on the universe select screen),
        # then we can skip the rest of the loading logic.
        if (meta_only):
            return
        """ End quick load check """


        # Check for achievements definitions
        path = os.path.join( UNIVERSES_PATH, self.name, "achievements.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create node from the file path
            ref = XMLParser().create_node_from_file(path).find_node_by_tag("achievements")

            # Validate
            if (ref):

                # Loop defined achievements
                for ref_achievement in ref.get_nodes_by_tag("achievement"):

                    # Create a new achievement
                    achievement = Achievement()

                    # Load state using the current node
                    achievement.load_state(ref_achievement)


                    # Add it to this universe's achievements list
                    self.achievements.append(achievement)


            # Load in previously unlocked achievements (global across all "new games")
            control_center.load_unlocked_achievements(universe = self)


        # Check for default session data
        path = os.path.join( UNIVERSES_PATH, self.name, "session.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create a node from the default session data, then find the session node
            ref_session = XMLParser().create_node_from_file(path).find_node_by_tag("session")

            # Validate
            if (ref_session):

                # Set up a session hash
                session = {}

                # Grab variables
                variable_collection = ref_session.get_nodes_by_tag("variable")

                # Add to temp session
                for ref_variable in variable_collection:

                    # Hash
                    session[ ref_variable.get_attribute("name") ] = ref_variable.get_attribute("value")

                # Ask the universe to import the given default session data.
                self.import_session(session)

                """
                    key = "%s" % ref_variable.get_attribute("key")

                    default = "%s" % ref_variable.get_attribute("default")
                    value = "%s" % ref_variable.get_attribute("value")

                    # Create a session variable object
                    self.session[key] = SessionVariable(default)

                    # I guess we'll update with current value.  Not sure why this would ever differ from default, but why not?
                    self.session[key].set_value(value)

                    # Overwrite / create session variable according to the default
                    #self.session[key] = {
                    #    "default": default,
                    #    "value": value
                    #}
                """


        # Check to see if this universe defines items
        path = os.path.join( UNIVERSES_PATH, self.name, "items.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create an xml wrapper node from the file, then find the hard item data node
            ref_item_data = XMLParser().create_node_from_file(path).find_node_by_tag("item-data")

            # Validate
            if (ref_item_data):

                # Check for predefined items
                ref_items = ref_item_data.find_node_by_tag("items")

                # Validate
                if (ref_items):

                    # Loop through each predefined item
                    for ref_item in ref_items.get_nodes_by_tag("item"):

                        # Create a new item
                        item = InventoryItem()

                        # Load item state
                        item.load_state(ref_item)

                        # Save item!
                        self.items.append(item)


                # Next, check for any defined item upgrade pool
                ref_upgrade_pools = ref_item_data.find_node_by_tag("upgrade-pools")

                # Validate
                if (ref_upgrade_pools):

                    # Get all pools
                    upgrade_pool_collection = ref_upgrade_pools.get_nodes_by_tag("upgrade-pool")

                    # Loop
                    for ref_upgrade_pool in upgrade_pool_collection:

                        # Create a new upgrade pool
                        upgrade_pool = UpgradePool()

                        # Load pool state (this populates all item upgrades within the pool as well)
                        upgrade_pool.load_state(ref_upgrade_pool)


                        # Save the new upgrade pool
                        self.upgrade_pools.append(upgrade_pool)


        # Check for universe scripts (i.e. global scripts)
        path = os.path.join( UNIVERSES_PATH, self.name, "global", "scripts.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create an xml wrapper node from the file, then find the hard item data node
            ref_scripts = XMLParser().create_node_from_file(path).find_node_by_tag("scripts")

            # Validate
            if (ref_scripts):

                # Loop scripts
                for ref_script in ref_scripts.get_nodes_by_tag("script"):

                    # We keep the script logic as innerText.
                    self.scripts[ ref_script.get_attribute("name") ] = ref_script.innerText


        # Check for universe conversations (i.e. global conversations)
        path = os.path.join( UNIVERSES_PATH, self.name, "global", "conversations.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create an xml wrapper node from the file, then find the hard item data node
            ref_conversations = XMLParser().create_node_from_file(path).find_node_by_tag("conversations")

            # Validate
            if (ref_conversations):

                # Loop conversations
                for ref_conversation in ref_conversations.get_nodes_by_tag("conversation"):

                    # NPCs import conversations from xml nodes.  Thus, we'll just
                    # keep a reference to the node we found.  NPCs can use them as they need them.
                    self.conversation_nodes[ ref_conversation.get_attribute("id") ] = ref_conversation


        # Did this universe's maps data file specify a primary map?
        # We've loaded all of the data, and now we're ready to activate the primary map.
        if (primary_map_name != None):

            # Remember primary map name in case we save the universe (in level editor)
            self.primary_map_name = primary_map_name

            # Activate the map
            self.activate_map_on_layer_by_name( self.primary_map_name, LAYER_FOREGROUND, game_mode = game_mode, control_center = control_center )


            # Center the camera on the primary map as we begin the universe
            self.get_active_map().center_camera_on_entity_by_name(self.camera, "player1", zap = True)


        # At the end, let's load in the stats that describe the various attributes of each
        # skill/level in the game.  This can theoretically differ from universe to universe.
        for skill in SKILL_LIST:

            # Stored by skill name
            path = os.path.join( self.get_working_skill_data_path(), "%s.xml" % skill )

            # Validate
            if ( os.path.exists(path) ):

                # Read in the xml data
                f = open(path, "r")
                xml = f.read()
                f.close()

                # Parse the xml
                root = XMLParser().create_node_from_xml(xml).get_first_node_by_tag("*")

                # Define skill stats by that node; we will only populate data relevant to the current skill (we're not resetting or overwriting any other skill).
                self.skill_stats.load_from_node(root)


    # Save data to file...
    def save(self):

        # Make sure we have a path ready to save data for this universe...
        path = os.path.join( "universes", self.name )

        # Ensure that the path exists
        ensure_path_exists(path)


        # Create a node for map data
        node = XMLNode("maps")

        # Add a node for the primary map
        node.add_node(
            XMLNode("primary-map").set_attributes({
                "name": self.primary_map_name
            })
        )

        # Create a node for background maps
        ref_background_maps = node.add_node(
            XMLNode("background")
        )

        # Add in each background map
        for key in sorted( self.map_data[LAYER_BACKGROUND] ):

            ref_background_maps.add_node(
                self.map_data[LAYER_BACKGROUND][key].save_state()
            )


        # Create a node for foreground maps
        ref_foreground_maps = node.add_node(
            XMLNode("foreground")
        )

        # Add in each foreground map
        for key in sorted( self.map_data[LAYER_FOREGROUND] ):

            ref_foreground_maps.add_node(
                self.map_data[LAYER_FOREGROUND][key].save_state()
            )

        # Save map data
        f = open( os.path.join("universes", self.name, "maps.xml"), "w" )
        f.write( node.compile_xml_string() )
        f.close()


        # Create a node for session variables
        node = XMLNode("session")

        # Grab session keys
        keys = self.session.keys()

        # I want to save everything in alphabetical order
        keys.sort()

        # Loop through and add each session variable
        for key in keys:

            node.add_node(
                XMLNode("variable").set_attributes({
                    "key": key,
                    "default": xml_encode( self.session[key].get_default() ),
                    "value": xml_encode( self.session[key].get_value() )
                })
            )

        # Save session variable data
        f = open( os.path.join("universes", self.name, "session.xml"), "w" )
        f.write( node.compile_xml_string() )
        f.close()


        """
        NOTE:  I can't think of a reason why I would need to save quest / item data when saving
               the universe.  I don't think I ever edit in within the editor.  I generate all of
               it via external scripts and web applications, so it's basically read-only.
               I'll comment it out for now.

        # Create a node to hold quest data
        node = XMLNode("quests")

        # Loop quests
        for quest in self.get_quests():

            # Create a node for this quest
            ref_quest = node.add_node(
                XMLNode("quest").set_attributes({
                    "name": xml_encode( quest.get_name() ),
                    "title": xml_encode( quest.get_title() )
                })
            )

            # Add quest description
            ref_quest.add_node(
                XMLNode("description").set_inner_text( quest.get_description() )
            )

            # Loop quest updates
            for update in quest.updates:

                ref_quest.add_node(
                    XMLNode("update").set_attributes({
                        "name": xml_encode( update.get_name() )
                    }).set_inner_text( update.get_description() )
                )

        # Save quest data
        f = open( os.path.join("universes", self.name, "quests.xml"), "w" )
        f.write( node.compile_xml_string() )
        f.close()


        # Create a node for all item data (upgrade pools, item templates, et al.)
        node = XMLNode("item-data")


        # Create a node for item templates
        ref_items = node.add_node(
            XMLNode("items")
        )

        # Loop items
        for item in self.items:

            ref_items.add_node(
                item.save_state()
            )


        # Create another node for upgrade pools
        ref_upgrade_pools = node.add_node(
            XMLNode("upgrade-pools")
        )

        # Loop upgrade pools
        for upgrade_pool in self.upgrade_pools:

            ref_upgrade_pools.add_node(
                upgrade_pool.save_state()
            )


        # Save item data to disk
        f = open( os.path.join("universes", self.name, "items.xml"), "w" )
        f.write( node.compile_xml_string() )
        f.close()
        """


    # Update the "last played" date for this universe.
    def update_last_played_date(self):

        # Open lastplayed.txt file in universe folder
        f = open( os.path.join( self.get_working_save_data_path(), "lastplayed.txt" ), "w" )

        # Write timestamp
        f.write(
            "%s" % time.time()#get_formatted_time() # utils function
        )

        # Done
        f.close()


    # Generate a thumbnail from the current screen display.
    # We'll display this to the user when they choose to load a previous save.
    def generate_filesave_thumbnail(self):

        # Make sure ./tmp folder exists
        ensure_path_exists("tmp")

        # Save the current display to a temporary file, just to stay consistent.
        # We'll never present this image to the user directly.
        pygame.image.save(
            pygame.display.get_surface(),
            os.path.join("tmp", "temp_surface.png")
        )

        resize_image( os.path.join("tmp", "temp_surface.png"), os.path.join("tmp", "temp_surface.resized.png"), size = (160, 120) )


    # End a session, calling the onunload script for any visible map
    def end_session(self, control_center, universe):

        # Loop visible maps on the foreground layer
        for m in self.visible_maps[LAYER_FOREGROUND].values():

            # Execute (immediately and in full) the onunload script
            m.execute_script("onunload", control_center, universe)


    # Create a dummy session for GIFs, "movies," etc.  It just needs a few common variables.
    def create_dummy_session(self):

        # Set up a dummy session
        dummy_session = {
            "app.active-map-name": SessionVariable(""),

            "core.is-gif": SessionVariable("1"),

            "core.is-dummy-session": SessionVariable("1"),

            "core.player1.name": SessionVariable("Player"),
            "core.player-id": SessionVariable("1"),

            "core.x": SessionVariable("0"),
            "core.y": SessionVariable("0"),

            "core.xp-bar.timer": SessionVariable("0"),

            "core.gold.found": SessionVariable("0"),
            "core.gold.wallet": SessionVariable("0"),
            "core.gold.wallet:visible": SessionVariable("0"),       # Don't know that I really need this here

            "core.bombs.count": SessionVariable("10")
        }

        for key in SKILL_LIST:

            dummy_session["core.skills.%s" % key] = SessionVariable("3")

            dummy_session["core.skills.%s:timer" % key] = SessionVariable("0")
            dummy_session["core.skills.%s:timer-max" % key] = SessionVariable("0")

            dummy_session["core.skills.%s:timer-drain" % key] = SessionVariable("0")
            dummy_session["core.skills.%s:timer-drain-while-motionless" % key] = SessionVariable("0")

        return dummy_session


    # Get the name of the universe (i.e. folder path)
    def get_name(self):

        return self.name


    # Get the release version of this universe (used for keeping netplay sessions in sync)
    def get_version(self):

        return self.version


    # Get the readable title of the universe
    def get_title(self):

        return self.title


    # Get the universe's type (story?  linear?)
    def get_type(self):

        # Return
        return self.type


    # Get minimum player count
    def get_min_players(self):

        # Return
        return self.min_players


    # Get maximum player count
    def get_max_players(self):

        # Return
        return self.max_players


    # Get a list of all maps available to a potential level selector screen.
    # This might return an empty list, indicating that we should not offer such a screen...
    def get_selectable_levels(self):

        # Results
        results = []


        # Check for the metadata file, which holds level selection data
        path = os.path.join( UNIVERSES_PATH, self.name, "meta.xml" )

        # Validate
        if ( os.path.exists(path) ):

            # Create a node from the meta file data
            ref = XMLParser().create_node_from_file(path).find_node_by_tag("metadata")

            # Check for selectable levels
            ref_selectable_levels = ref.find_node_by_tag("selectable-levels")

            # Validate
            if (ref_selectable_levels):

                # Loop members
                for ref_selectable_level in ref_selectable_levels.get_nodes_by_tag("selectable-level"):

                    # Add the level name to our results
                    results.append(
                        ref_selectable_level.innerText
                    )


        # Return selectable level names
        return results


    # Return a confirmed-as-existing path to the universe's map data
    def get_working_map_data_path(self, alternate_universe = None):

        universe_name = self.name

        # Sometimes we want to source from an alternate universe (usually for gifs)
        if (alternate_universe):

            universe_name = alternate_universe


        # Define the working path for the current user in this universe
        path = os.path.join("universes", universe_name, "maps")

        # I'm not going to lie.  If the path doesn't exist for whatever reason, the user is kind of screwed.
        # They probably deleted the files for some bizarre reason.  I guess we can make sure it exists anyway...
        create_path(path)

        # Return the confirmed-as-existing path
        return path


    def get_working_skill_data_path(self):

        # Define working path for the current universe
        path = os.path.join("universes", self.name, "skill.data")

        # Return
        return path


    def get_working_save_data_path(self):

        # Define the working path for the current user in this universe
        #path = os.path.join("sessions", self.get_session_variable("core.player1.name").get_value(), "universes", self.name)
        path = os.path.join("user", "sessions", "universes", self.name)

        # Make sure that path exists fully!
        create_path(path)

        # Return the confirmed-as-existing path
        return path


    def get_skill_stats(self):

        return self.skill_stats


    # Get the achievements list
    def get_achievements(self):

        # Return
        return self.achievements


    # Get an achievement by its given name
    def get_achievement_by_name(self, name):

        # Loop achievements
        for achievement in self.get_achievements():

            # Match?
            if ( achievement.get_name() == name ):

                # Return
                return achievement


        # Couldn't find it
        return None


    # Execute a given achievement hook
    def execute_achievement_hook(self, name, control_center):

        # If we haven't yet cached the particular achievements that contain this hook,
        # we'll do so now.
        if ( not (name in self.achievement_hook_cache) ):

            # Initialize
            self.achievement_hook_cache[name] = []

            # Loop all achievements
            for achievement in self.achievements:

                # Does this achievement use the given hook?
                if ( achievement.has_hook(name) ):

                    # Add it to the cache
                    self.achievement_hook_cache[name].append(achievement)


        # Create a new, temporary event controller
        event_controller = control_center.create_event_controller()


        # At this point, we have ensured an up-to-date cache.
        # Let's now execute the given hook for all achievements in the appropriate cache.
        # Note that we only care about active achievements.
        for achievement in [ o for o in self.achievement_hook_cache[name] if o.is_active() ]:

            # Load the compiled script
            event_controller.load(
                achievement.get_hook(name)
            )

            # Run for as long as we can
            event_controller.loop(control_center, universe = self)


    # Get map data for a map by a given name, on any layer
    def get_map_data(self, name):

        # Check layers
        for layer in self.map_data:

            # Loop data objects
            for o in self.map_data[layer].values():

                # Match?
                if ( o.get_name() == name ):

                    # Return map data object
                    return o

        # 404
        return None


    # Get map data for maps in a given class.  No wildcarding support, currently.
    def get_map_data_by_class(self, class_name):

        # Track results
        results = []

        # Loop layers
        for layer in self.map_data:

            # Loop map data objects
            for o in self.map_data[layer].values():

                # Match class?
                if ( o.has_class(class_name) ):

                    # Add to results
                    results.append(o)

        # Return results
        return results


    # Fetch common input translations (e.g. which keys move left, right, etc.) and
    # save them as built-in session variables.
    def update_common_input_translations(self, control_center):

        # Reference to input controller
        input_controller = control_center.get_input_controller()

        # This is lame-ish, but I'm just going to hard-code in the movement names, for now at least.
        common_input_keys = ("left", "right", "up", "down", "dig-left", "dig-right", "dig-forward", "bomb", "suicide", "interact", "minimap", "skill1", "skill2", "enter")

        # Loop keys
        for key in common_input_keys:

            # Save to session, directly
            self.get_session_variable("sys.input.keyboard.%s" % key).set_value(
                input_controller.fetch_keyboard_translation(key).upper()
            )

            # Also save gamepad translation
            self.get_session_variable("sys.input.gamepad.%s" % key).set_value(
                input_controller.fetch_gamepad_translation(key).upper()
            )


    def session_variable_exists(self, key):

        return ( key in self.session )


    def get_session_variable(self, key):

        if (key in self.session):

            return self.session[key]

        else:

            # Create implicitly, default to "0"
            self.session[key] = SessionVariable("0")

            log_msg( "Warning:  Session Variable '%s' does not exist!  Creating implicitly!" % key )
            # Return
            return self.session[key]


    def get_session_variable_using_session(self, key, session):

        if (key in session):

            return session[key]["value"]

        else:

            log_msg( "Warning:  Session Variable '%s' does not exist in supplied session!" % key )
            return 0


    # This used to directly set value on a hash key.
    # Now it's going to implicitly retrieve a session variable object and then set its value.  **Hacky-ish, because I really don't want to replace all calls with .get.set throughout every script.
    def set_session_variable(self, key, value):

        if (key in self.session):

            self.get_session_variable(key).set_value(value)

        else:

            log_msg( "Warning:  Session Variable '%s' does not exist!" % key )
            return


    def set_session_variable_using_session(self, key, value, session):

        if (key in session):

            session[key]["value"] = value

        else:

            log_msg( "Warning:  Session Variable '%s' does not exist in supplied session!" % key )
            return


    # See set_session_variable for why this is hacky and implicit.
    def increment_session_variable(self, key, amount):

        if (key in self.session):

            self.get_session_variable(key).increment_value(amount)


    def increment_session_variable_using_session(self, key, amount, session):

        if (key in session):

            # Might not be numeric?
            try:

                # Get current value
                current_value = int( session[key]["value"] )

                # Increment, set
                self.set_session_variable_using_session(key, "%d" % (current_value + amount), session)

            except:
                log_msg( "Warning:  Session Variable '%s' is not numeric in supplied session!" )

        else:

            log_msg( "Warning:  Session Variable '%s' does not exist in supplied session!" % key )
            return


    def translate_session_variable_references(self, message, control_center):

        # Replace referenced session variables
        for key in self.session:

            message = message.replace("$[%s]" % key, self.get_session_variable(key).get_value())


        # We use the phrase "@enter," along with a couple of other input phrases, as a special case.  The translation depends on which device
        # the player more recently used to play the game.
        if (control_center):

            # Keyboard?
            if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ):

                # Replace with keyboard "interact" translation
                message = message.replace( "@enter", self.get_session_variable("sys.input.keyboard.interact").get_value() )

                # Replace other input texts
                for key in ("dig-left", "dig-right", "dig-forward", "left", "right", "up", "bomb"):

                    # Replace with keyboard translation
                    message = message.replace(
                        "@%s" % key,
                        self.get_session_variable("sys.input.keyboard.%s" % key).get_value()
                    )

            # No.  Assume gamepad.
            else:

                # Replace with gamepad "interact" translation
                message = message.replace( "@enter", self.get_session_variable("sys.input.gamepad.interact").get_value() )

                # Replace other input texts
                for key in ("dig-left", "dig-right", "dig-forward", "left", "right", "up", "bomb"):

                    # Replace with gamepad translation
                    message = message.replace(
                        "@%s" % key,
                        self.get_session_variable("sys.input.gamepad.%s" % key).get_value()
                    )


        # Return translated string
        return message


    # Add a new historical record to a given type of historical records
    def add_historical_record(self, group, s):

        # Make sure group exists
        if ( not (group in self.historical_records) ):

            # Default to empty list
            self.historical_records[group] = []

        # Add record (raw string data)
        self.historical_records[group].append(s)


    # Check to see if a given historical record exists, within a given group
    def has_historical_record(self, group, s):

        logn( "universe history debug", "Record check:  ", (group, s) )

        # Validate group
        if (group in self.historical_records):

            logn( "universe history debug", "Record check:  YES" )
            # Check list
            return (s in self.historical_records[group])

        else:
            return False


    # Get all historical records of a given type
    def get_historical_records_by_type(self, group):

        # Validate
        if (group in self.historical_records):

            # REturn all
            return self.historical_records[group]

        # If no such group exist, return an empty list
        else:

            return []


    # Get a universe (i.e. global) conversation node, by id
    def get_conversation_node(self, conversation_id):

        # Validate
        if (conversation_id in self.conversation_nodes):

            # Return the node
            return self.conversation_nodes[conversation_id]

        else:
            return None


    # Fetch the universe's timer controller
    def get_timer_controller(self):

        return self.timer_controller


    # Pause the game (iteratively)
    def pause(self):

        # Increment pause count
        self.pause_count += 1


        # For chaining
        return self


    # Unpause the game (maybe)
    def unpause(self, force = False):

        # Force to 0?  (Risky?)
        if (force):

            # Force to 0
            self.pause_count = 0

        else:

            # One less
            self.pause_count -= 1

            # Don't go negative
            if (self.pause_count < 0):
                self.pause_count = 0


        # For chaining
        return self


    # Check pause status
    def is_paused(self):

        return (self.pause_count > 0)


    # Get the camera
    def get_camera(self):

        return self.camera


    # Center the universe camera on a given map object "m"
    def center_camera_on_map(self, m):

        # Local player id?
        player_id = int( self.get_session_variable("core.player-id").get_value() )

        # Center the camera object (with zap)
        m.center_camera_on_entity_by_name(self.camera, "player%d" % player_id, zap = True)

        # We've fulfilled the request (or've tried to)...
        m.center_camera_immediately = False


        # If our prerender status is currently pending, then we can probably set it to ready now...
        if (self.prerender_status == PRERENDER_STATUS_PENDING):

            # Just confirm that the camera centered successfully
            if ( (self.camera.x == self.camera.target_x) and (self.camera.y == self.camera.target_y) ):

                # Update flag to ready (for the .draw_game function).
                self.prerender_status = PRERENDER_STATUS_READY


    # Get the universal region for a given map on a given layer
    def get_base_region_for_map_on_layer(self, name, layer, scale = None):

        # Validate
        if ( name in self.map_data[layer] ):

            # Convenience
            data = self.map_data[layer][name]

            # If we don't specify a scale, assume default scale for the given layer
            scale = coalesce( scale, SCALE_BY_LAYER[layer] )

            # Calculate simple bounds
            return (
                int(data.x * TILE_WIDTH * scale),
                int(data.y * TILE_HEIGHT * scale),
                int(data.width * TILE_WIDTH * scale),
                int(data.height * TILE_HEIGHT * scale)
            )

        # 404
        else:
            return (0, 0, 0, 0)


    # Get the final render region for a given map on a given layer
    def get_render_region_for_map_on_layer(self, name, layer, scale = None, parallax = None, zoom = 1.0):

        # Validate map name
        if ( name in self.map_data[layer] ):

            # Get map data
            m = self.map_data[layer][name]

            # Use either the given scale/parallax values or the default values for the given layer
            scale = coalesce( scale, zoom * SCALE_BY_LAYER[layer] )
            parallax = coalesce( parallax, zoom * PARALLAX_BY_LAYER[layer] )

            # Convenience
            (cameraX, cameraY) = (
                int(zoom * self.camera.x),
                int(zoom * self.camera.y)
            )

            # Absolute active map world position
            (map_x, map_y) = (
                int(scale * m.x * TILE_WIDTH),
                int(scale * m.y * TILE_HEIGHT)
            )

            # Retrieve parallax offsets at the given camera position
            (px, py) = self.camera.get_parallax_offsets_at_location(cameraX, cameraY, parallax = parallax)

            # Calculate where on the screen this map should render at the moment.
            # Also calculate the dimensions of the map, according to scale.
            return (
                map_x + px - cameraX,
                map_y + py - cameraY,
                int( (m.width * TILE_WIDTH) * scale ),
                int( (m.height * TILE_HEIGHT) * scale )
            )

        else:

            # Return an "empty" rectangle
            return (0, 0, 0, 0)


    # Get the region a camera can span for a given map on a given layer (this should always be the foreground layer, though...)
    def get_camera_region_for_map_on_layer(self, name, layer):

        # Validate
        if ( name in self.map_data[layer] ):

            # Calculate the region in which the camera can scroll
            # (thus including the maximum perimeter wander).
            rPerimeter = offset_rect(
                self.get_base_region_for_map_on_layer(name, layer),
                x = -MAX_PERIMETER_SCROLL_X,
                y = -MAX_PERIMETER_SCROLL_Y,
                w = (2 * MAX_PERIMETER_SCROLL_X),
                h = (2 * MAX_PERIMETER_SCROLL_Y)
            )


            # The camera region must at least equal the resolution of the game
            if ( rPerimeter[2] < SCREEN_WIDTH ):

                # How much room to spare?
                dx = (SCREEN_WIDTH - rPerimeter[2])

                # Pack
                rPerimeter = offset_rect(
                    rPerimeter,
                    x = -int(dx / 2),
                    w = dx
                )

            # Check y-axis as well
            if ( rPerimeter[3] < SCREEN_HEIGHT ):

                # How much spare room?
                dy = (SCREEN_HEIGHT - rPerimeter[3])

                # Pack
                rPerimeter = offset_rect(
                    rPerimeter,
                    y = -int(dy / 2),
                    h = dy
                )


            # Return rectangle
            return rPerimeter


        # 404
        else:
            return (0, 0, 0, 0)


    def is_busy(self):

        if (self.overworld_menu):

            return (self.overworld_menu.is_dismissed == False)

        else:

            return False


    def lock_with_key(self, key, timeout = 30, strength = None, f_on_unlock = None, f_on_timeout = None):

        if (not (key in self.locks)):

            self.locks[key] = {
                "on-unlock": f_on_unlock,
                "on-timeout": f_on_timeout,
                "lock-strength": strength,
                "timestamp": time.time()
            }

        #self.lock_count = len(self.locks)
        self.lock_count = sum( int( self.locks[e]["lock-strength"] in (LOCK_SOFT, LOCK_HARD) ) for e in self.locks )

        self.under_soft_lock = any( self.locks[e]["lock-strength"] in (LOCK_SOFT, LOCK_HARD) for e in self.locks )

        self.under_hard_lock = any( self.locks[e]["lock-strength"] in (LOCK_HARD,) for e in self.locks )


    def unlock(self, key):

        if (key in self.locks):

            settings = self.locks.pop(key)

            if ( settings["on-unlock"] ):

                settings["on-unlock"]()


            log( "Lock '%s' unlocked in approximately '%s'" % (key, (time.time() - settings["timestamp"])) )

        #self.lock_count = len(self.locks)
        self.lock_count = sum( int( self.locks[e]["lock-strength"] in (LOCK_SOFT, LOCK_HARD) ) for e in self.locks )

        self.under_soft_lock = any( self.locks[e]["lock-strength"] in (LOCK_SOFT, LOCK_HARD) for e in self.locks )

        self.under_hard_lock = any( self.locks[e]["lock-strength"] in (LOCK_HARD,) for e in self.locks )

        #self.under_soft_lock = ( len(self.locks) > 0 )

        #self.under_hard_lock = lambda a = any( self.locks[e]["hard-lock"] == True for e in self.locks ): a


    def is_locked(self):

        return self.under_hard_lock


    def is_soft_locked(self):

        return self.under_soft_lock


    def get_net_player_name_by_player_id(self, player_id, network_controller):

        return self.get_session_variable("net.player%d.nick" % player_id).get_value()

        # Has this player id joined the game yet?
        if ( player_id in network_controller.get_player_ids() ):

            # Return the player's chosen nick
            return self.get_session_variable("net.player%d.nick" % player_id).get_value()

        # Nope.  Next, see if this player ID can even join the game...
        elif ( player_id <= int( self.get_session_variable("net.player-limit").get_value() ) ):

            # Return a generic player nick
            return "Player %d" % player_id


        # This player can't even join the game, it's over the limit.
        else:

            return "n/a"#Player n/a"


    def get_net_player_status_by_player_id(self, player_id, network_controller):

        # Sanity check
        if ( player_id <= int( self.get_session_variable("net.player-limit").get_value() ) ):

            # Player online?
            if ( 1 == int( self.get_session_variable("net.player%d.joined" % player_id).get_value() ) ):

                # Ready / not ready?
                return ( "Ready" if self.get_session_variable("net.player%d.ready" % player_id).get_value() == "1" else "Not Ready" )

            # Waiting for player...
            else:

                return "Waiting..."

        else:

            return "n/a"



        return "Unknown"

        # Has this player id joined the game yet?
        if ( player_id in network_controller.get_player_ids() ):

            # Return the player's ready/not ready status
            if ( int( self.get_session_variable("net.player%d.ready" % player_id).get_value() ) == 1 ):

                return "Ready!"

            else:

                return "Not ready"

        # Nope.  Next, see if this player ID can even join the game...
        elif ( player_id < int( self.get_session_variable("net.player-limit").get_value() ) ):

            # Return a "slot open" type of message
            return "Waiting for player"


        # This player can't even join the game, it's over the limit.
        else:

            return ""#n/a"





    def process_network_command(self, command, control_center):

        # We might well need the network controller
        network_controller = control_center.get_network_controller()


        log2( "Process:  '%s'" % command.get_command() )

        (param1, remainder) = ("", "")

        pieces = command.get_command().split(";", 1)

        command_type = int( pieces[0] )

        if ( len(pieces) > 1 ):
            remainder = pieces[1]

        (data, source) = (
            remainder,
            command.get_source()
        )


        if (command_type == NET_MSG_ENTITY_START_MOTION):

            network_controller.recv_entity_start_motion(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_ENTITY_STOP_MOTION):

            network_controller.recv_entity_stop_motion(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_ENTITY_DIG):

            network_controller.recv_entity_dig(data, source, control_center, universe = self)

        elif (command_type == NET_REQ_CONFIRM_DIG_TILE):

            network_controller.recv_entity_dig_validation_request(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_ENTITY_DIG_RESPONSE_VALID):

            network_controller.recv_entity_dig_success(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_INVALIDATE_DIG):

            network_controller.recv_entity_dig_failure(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_PLAYER_ID):

            network_controller.recv_player_id(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_PING):

            network_controller.recv_ping(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_PONG):

            network_controller.recv_pong(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_UNLOCK):

            network_controller.recv_unlock(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_SYNC_ONE_GOLD):

            network_controller.recv_sync_one_gold(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_CREATE_BOMB):

            network_controller.recv_create_bomb(data, source, control_center, universe = self)

        elif (command_type == NET_REQ_VALIDATE_BOMB):

            network_controller.recv_bomb_validation_request(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_VALIDATE_BOMB_OK):

            network_controller.recv_bomb_success(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_VALIDATE_BOMB_UNAUTHORIZED):

            network_controller.recv_bomb_failure(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_ENTITY_DIE):

            network_controller.recv_entity_die(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_ENTITY_RESPAWN):

            network_controller.recv_entity_respawn(data, source, control_center, universe = self)

        elif (command_type == NET_REQ_CALL_SCRIPT):

            network_controller.recv_script_request(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_CALL_SCRIPT):

            network_controller.recv_call_script(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_SYNC_ENEMY_AI):

            network_controller.recv_sync_enemy_ai(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_SYNC_PLAYER_BY_ID):

            network_controller.recv_sync_player_by_id(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_VOTE_TO_SKIP):

            network_controller.recv_vote_to_skip(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_TRANSITION_TO_MAP):

            network_controller.recv_transition_to_map(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_BEGIN_GAME):

            network_controller.recv_begin_game(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_LEVEL_COMPLETE):

            network_controller.recv_level_complete(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_LEVEL_FAILED):

            network_controller.recv_level_failed(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_CHAT):

            network_controller.net_console.add(remainder)

        elif (command_type == NET_MSG_REQ_NICK):

            network_controller.recv_req_nick(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_SYNC_PLAYER):

            network_controller.recv_sync_player(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_SYNC_ALL_PLAYERS):

            network_controller.recv_sync_all_players(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_SERVER_DISCONNECTING):

            network_controller.recv_server_disconnecting(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_CLIENT_DISCONNECTING):

            network_controller.recv_client_disconnecting(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_CONFIRM_DISCONNECT):

            network_controller.recv_confirm_disconnect(data, source, control_center, universe = self)

        elif (command_type == NET_MSG_AVATAR_DATA):

            network_controller.recv_avatar_data(data, source, control_center, universe = self)


    # Prepare session data in advance of beginning a co-op level
    def prepare_multiplayer_session(self):

        # Colorify all players (or hide them if they did not join)
        for player_id in range(1, 5):

            # If we can't find the related player id on the map, then this is all irrelevant...
            player = self.get_active_map().get_entity_by_name("player%d" % player_id)

            # Validate
            if (player):

                # Did this player join the session?
                if ( int( self.get_session_variable("net.player%d.joined" % player_id).get_value() ) == 1 ):

                    player.set_status(STATUS_ACTIVE)

                    # Colorify the player
                    player.colorify( self.get_session_variable("net.player%d.avatar.colors" % player_id).get_value() )

                # No?  Hide this avatar, then...
                else:
                    player.set_status(STATUS_INACTIVE)


        # Add in an extra delay for the enemies so that all players
        # can get their bearings as the lobby widget disappears.
        for e in self.get_active_map().get_entities_by_type(GENUS_ENEMY):

            # 200% increase in delay
            e.hesitate(
                e.get_hesitation_value() + (2 * AI_ENEMY_INITIAL_DELAY)
            )


    # Prepare session data for a new lobby
    def prepare_multiplayer_lobby(self):

        # Reset vote to skip trackers
        self.set_session_variable("net.votes-to-skip", "0")
        self.set_session_variable("net.already-voted-to-skip", "0")

        # Game is not in progress yet
        self.set_session_variable("net.game-in-progress", "0")

        # Countdown does not start until all players are ready
        self.set_session_variable("net.countdown-in-progress", "0")


        # Set each player's status to not ready
        for i in range(1, 5):

            self.set_session_variable("net.player%d.ready" % i, "0")


    # Erase any data we had for a player who has now left the game
    def clear_net_player_data_in_slot(self, slot):

        # Remove the given player entity from the map
        self.get_active_map().remove_entity_by_name("player%d" % slot)

        # Remove any possible respawn for this player as well (they may have quit while dead and awaiting respawn)
        self.get_active_map().remove_entity_by_name("player%d.respawn" % slot)


        # Joined status is 0
        self.set_session_variable("net.player%d.joined" % slot, "0")

        # Haven't received nick
        self.set_session_variable("net.player%d.received-nick" % slot, "0")

        # Default nick
        self.set_session_variable("net.player%d.nick" % slot, "Player %d" % slot)

        # Not ready, no player in this slot
        self.set_session_variable("net.player%d.ready" % slot, "0")


        # Lastly, flag that we need to rebuild the lobby to reflect new player data (this one has an effect
        # if the lobby is showing on the screen, of course)...
        self.set_session_variable("net.rebuild-intro-menu", "1")


    #def create_map(self, name = "Untitled Map", x = 0, y = 0, is_new = False, widget_dispatcher = None, network_controller = None, universe = None, session = None, quests = None, is_editor = False, alternate_universe = None):
    def create_map(self, name = "Untitled", x = 0, y = 0, options = {}, control_center = None):

        # Create a new map
        m = Map(name, x, y, options, control_center, parent = self)#is_new, network_controller, self, session, widget_dispatcher, self.quests, is_editor, alternate_universe)

        # Validate that we didn't incur an error (e.g. in editor mode and map already exists)
        if ( m.is_valid() ):

            # Return the new map object
            return m

        # Otherwise, return no map
        else:

            return None


    # Fetch the local player (player1 when offline, client player when online)
    def get_local_player(self):

        # Fetch active map
        m = self.get_active_map()

        # Validate
        if (m):

            logn( "universe player debug", "player%s" % self.get_session_variable("core.player-id").get_value() )

            # Get player according to local player id
            player = m.get_entity_by_name("player%s" % self.get_session_variable("core.player-id").get_value())

            # Return player
            return player

        # 404
        else:
            return None


    # Create a player on the active map by a given name at a given location.
    # (Overwrite any existing player object with the given name.)
    def spawn_player_with_name_at_location(self, name, x, y):

        # Debug
        log2( "**create player '%s' at position: (%d, %d)\n" % (name, x, y) )


        # Just in case, remove any player entity by the given name on the new map (i.e. overwrite entity with given name)
        self.visible_maps[LAYER_FOREGROUND][self.active_map_name].remove_entity_by_type_and_name(GENUS_PLAYER, name)

        # Create a player object on the new map and place it at the indicated spawn point..
        new_player = self.get_active_map().create_player().describe({
            "name": name,
            "genus": GENUS_PLAYER,
            "absolute-x": x,
            "absolute-y": y
        })

        # Now, add the player to the new map...
        self.visible_maps[LAYER_FOREGROUND][self.active_map_name].master_plane.entities[GENUS_PLAYER].append( new_player )


    # Mark a map as visible on the worldmap (out of the fog of war, but not necessarily visited)
    def set_map_as_visible(self, map_name):

        # Only foreground maps appear on the world map
        if (map_name in self.map_data[LAYER_FOREGROUND]):

            self.map_data[LAYER_FOREGROUND][map_name].visible = True


    # Mark a map as visited on the worldmap
    def set_map_as_visited(self, map_name):

        # Only foreground maps appear on the world map
        if (map_name in self.map_data[LAYER_FOREGROUND]):

            # Flag as visited
            self.map_data[LAYER_FOREGROUND][map_name].visited = True

            # Inherently, visiting a map will also render it "visible"...
            self.set_map_as_visible(map_name)


    # Check visited status
    def is_map_visited(self, map_name):

        # Only foreground maps appear on the world map
        if (map_name in self.map_data[LAYER_FOREGROUND]):

            # Return status
            return self.map_data[LAYER_FOREGROUND][map_name].is_map_visited()


    # Activate a given map by name.  Only foreground maps can be active.
    # When we set ignore_adjacent_maps to True, we load only the given map (i.e. linear universe levels).
    def activate_map_on_layer_by_name(self, map_name, layer, game_mode = MODE_GAME, control_center = None, ignore_adjacent_maps = False):#widget_dispatcher = None, network_controller = None):

        # Debug
        self.clear_item_attribute_result_cache()


        # Validate
        if (map_name in self.map_data[layer]):

            # Before we leave whatever map we were on, handle the departure logic...
            if (self.get_active_map()):

                self.get_active_map().handle_player_departure(control_center, universe = self)


            # First, let's update the active map name
            self.active_map_name = map_name

            # Track in session
            self.get_session_variable("app.active-map-name").set_value(map_name)


            # Before marking the map in any way (visited, visible, etc.), let's
            # build the map data (load the active map, if necessary, and load
            # any perimeter map.
            ##self.build_active_map_data(game_mode, control_center)#widget_dispatcher, network_controller)
            self.build_map_on_layer_by_name(map_name, layer, game_mode, control_center, ignore_adjacent_maps = ignore_adjacent_maps)


            # Set the completion time to 0 on the map we just built.
            # We'll increment it as the player attempts to complete the level.
            self.get_active_map().reset_completion_time()


            # If we haven't visited the map before, let's quickly run the global map.first-visit script,
            # then mark it as visited.
            if ( not self.is_map_visited(map_name) ):

                # Now we're going to mark this new active map as visited (we're on it!)
                self.set_map_as_visited(map_name)

                # Now we'll run the global map.first-visit script.
                self.run_script("map.first-visit", control_center)


            # Mark all adjacent maps as, at the least, "seen"...
            if (map_name in self.adjacency_data):

                for adj_name in self.adjacency_data[map_name]:

                    self.set_map_as_visible(adj_name)



            # Game mode?  Run scripts...
            if (game_mode == MODE_GAME):

                # Run universal onvisit first, if/a
                self.run_script("global.map.onvisit", control_center)

                # Now run map onvisit, if/a
                self.get_active_map().run_script("onvisit", control_center, universe = self)


            # DISABLED
            # Onload should be for a pure load, not a visit.
            # Load doesn't happen if the player goes back and forth without going out of visible range of the map.
            # Only run visit call when activating a map, that's what I want here.
            """
            # Check to see if the map has an onload script
            if ( ( game_mode == MODE_GAME ) and ( self.get_active_map().does_script_exist("onload") ) ):

                # The onload script is typically just a bunch of flag settings and such,
                # so we make sure to run through everything we can immediately...
                self.get_active_map().run_script("onload", control_center, universe = self, execute_all = True)#network_controller, universe, session, quests, execute_all = True)
            """


            # Instruct the newly activated map to handle any logic relating to a player entering...
            if ( game_mode == MODE_GAME ):

                # Call the player arrival callback
                self.visible_maps[layer][map_name].handle_player_arrival(control_center, universe = self)

                # Execute the "new-level" achievement hook
                self.execute_achievement_hook( "new-level", control_center )


            # Let's flag the prerender state as pending; once the camera reaches this newly-activated
            # map, we'll change it to "ready" so that we can prerender.
            self.prerender_status = PRERENDER_STATUS_PENDING

            # Invalidate the splash controller
            control_center.get_splash_controller().invalidate()


            """
            # If this isn't a GIF, then we'll check to see if we should add a net lobby menu
            if ( self.get_session_variable("core.is-gif").get_value() != "1" ):


                # Fetch the network controller
                network_controller = control_center.get_network_controller()

                if ( network_controller.get_status() != NET_STATUS_OFFLINE ):

                    # We need the menu controller here;
                    menu_controller = control_center.get_menu_controller()

                    # as well as the widget dispatcher
                    widget_dispatcher = control_center.get_widget_dispatcher()


                    # Add a lobby menu
                    menu_controller.add(
                        widget_dispatcher.create_net_lobby()
                    )
            """


        # Return the currently active map
        return self.get_active_map()


    # Set the active map by name.
    # Note that only FOREGROUND maps can be active.
    def set_active_map_by_name(self, name):

        self.active_map_name = name


    # Push a given map onto the pushed map stack.
    # If this stack has any map, then get_active_map() will return the map on top of the stack.
    def push_map_as_active(self, m):

        # Layer-agnostic
        self.pushed_map_stack.append(m)


    # Remove the highest map from the pushed map stack.
    # Does nothing if the stack has no map.
    def pop_pushed_active_map(self):

        # Sanity
        if ( len(self.pushed_map_stack) > 0 ):

            # Pop
            self.pushed_map_stack.pop()


    # Get the active map (if there is one)
    def get_active_map(self):

        # Do we have an actively pushed map on the stack?
        if ( len(self.pushed_map_stack) > 0 ):

            # Return the highest map
            return self.pushed_map_stack[-1]

        # If not, return the "real" active map
        else:

            # Validate.  Only foreground maps can be active.
            if (self.active_map_name in self.visible_maps[LAYER_FOREGROUND]):

                return self.visible_maps[LAYER_FOREGROUND][self.active_map_name]

            # Well okay, in level editor you can go back and forth on layers...
            elif (self.active_map_name in self.visible_maps[LAYER_BACKGROUND]):

                return self.visible_maps[LAYER_BACKGROUND][self.active_map_name]

            # Guess we couldn't find it...
            else:

                return None


    # Get a given map (by name) on a given layer
    def get_map_on_layer_by_name(self, name, layer):

        # Make sure we've loaded a map by that name on that layer
        if ( self.loaded_map_on_layer_by_name(name, layer) ):

            # Return that map
            return self.visible_maps[layer][name]

        # Sorry
        else:

            return None


    def is_map_newborn(self, map_name):

        # If we have a record of "seeing" the map, then we've previously
        # loaded it.  As such, it is no longer a newborn...
        return (self.map_data[LAYER_FOREGROUND][map_name].visited == False)

    def set_map_gold_remaining(self, map_name, gold_remaining):

        if (map_name in self.map_data[LAYER_FOREGROUND]):

            self.map_data[LAYER_FOREGROUND][map_name].gold_remaining = gold_remaining

    def mark_map_as_completed(self, map_name):

        if (map_name in self.map_data[LAYER_FOREGROUND]):

            self.map_data[LAYER_FOREGROUND][map_name].mark_as_completed()

    def is_map_completed(self, map_name):

        if (map_name in self.map_data[LAYER_FOREGROUND]):

            return self.map_data[LAYER_FOREGROUND][map_name].is_map_completed()

        else:

            return False


    # Save linear progress after completing a given linear level.
    # This function marks the map as complete and then updates an autosave file
    # for the current universe.
    def save_linear_progress(self, control_center, universe):

        # Mark the map as completed, for starters
        universe.mark_map_as_completed( universe.get_active_map().name )

        # Update completion time for the current map's map data object, if the
        # time represents a new personal best (or the player has never completed this level).
        if ( (universe.get_active_map().get_completion_time() < universe.get_map_data( universe.get_active_map().name ).completion_time) or
             (universe.get_map_data( universe.get_active_map().name ).completion_time == 0) ):

            # Update best completion time
            universe.get_map_data( universe.get_active_map().name ).completion_time = universe.get_active_map().get_completion_time()


        """ Autosave """
        # Autosave to slot 1, allowing the game to remember that the player finished this level within the level set.
        save_controller = control_center.get_save_controller()

        # Get generic metadata.  We'll never really show to this to the player, the game manages loading/saving
        # automatically for linear level sets (single save system).
        xml = save_controller.construct_metadata_with_title("Autosave (Linear Data)", universe = universe)


        # Save current screen display for screenshot.
        # Note:  We don't ever show a "linear save" thumbnail to the user.
        #        It's used for data only (all linear saving/loading is automatic).
        self.generate_filesave_thumbnail()


        # I don't use these because I don't spawn the player at a given location when loading the universe,
        # but I'll set them to remain consistent with the other autosave sections.
        universe.set_session_variable("core.player1.x", "%d" % 0)
        universe.set_session_variable("core.player1.y", "%d" % 0)

        # Commit the save...
        save_controller.save_to_slot(slot = 1, universe = universe, autosave = True, metadata = xml)


    def get_visible_map_names(self):

        results = []

        for map_name in self.map_data[LAYER_FOREGROUND]:

            if ( (self.map_data[LAYER_FOREGROUND][map_name].visible == True) or (self.map_data[LAYER_FOREGROUND][map_name].visited == True) ):
                results.append(map_name)

        return results

    def get_map_title(self, map_name):

        if (map_name in self.map_data[LAYER_FOREGROUND]):
            return self.map_data[LAYER_FOREGROUND][map_name].title

        else:
            return "Untitled Area"

    def reset_world_map_data(self):

        for key in self.map_data[LAYER_FOREGROUND]:

            self.map_data[LAYER_FOREGROUND][key].reset_world_map_data()

    def update_data_for_maps_on_layer(self, map_collection, layer):

        for key in map_collection:

            map_collection[key].update_dimensions()

            self.map_data[layer][key].configure({
                #"title": map_collection[key].title,   # Don't set title; do this only manually within meta file
                "x": map_collection[key].x,
                "y": map_collection[key].y,
                "width": map_collection[key].width,
                "height": map_collection[key].height,
                "gold-count": map_collection[key].get_gold_count(),
                "layer": map_collection[key].layer
            })

    def add_map_to_layer(self, m, layer, control_center):

        # Prevent duplicates
        if ( m.name in self.map_data[layer] ):

            # Sorry
            return False

        else:

            # Add to specified layer's map data
            self.map_data[layer][m.name] = MapData().configure({
                "name": m.name,
                "title": m.title,
                "x": m.x,
                "y": m.y,
                "width": -1,
                "height": -1,
                "gold-count": 0,
                "layer": layer
            })

            log2(m, m.planes)

            # Save the new map
            m.save( os.path.join( self.get_working_map_data_path(), "%s.xml" % m.name) )

            # Activate the map.  Specify level editor mode, as we'll never "create a new map" in game...
            self.activate_map_on_layer_by_name(m.name, layer, game_mode = MODE_EDITOR, control_center = control_center )

            # Success!
            return True


    # Check to see if the universe has loaded a given map (by name) on a given layer
    def loaded_map_on_layer_by_name(self, name, layer):

        # Simple check
        return ( name in self.visible_maps[layer] )


    # Load and return a temporary map object, by map name.
    # Used in scripting to check map properties.
    def get_temporary_map_by_name(self, name):

        # First, attempt to create the map object
        m = self.create_map(
            name = name,
            x = 0,          # Not needed for a temp map, just looking up stats
            y = 0,          # (same)
            options = {
                "is-new": False
            },
            control_center = None            # Obsolete control_center param
        )

        # Validate
        if (m):

            # Load map data.  We're only going to load in the map data itself;
            # we'll skip dialogue/menu data.
            m.load(
                filepaths = {
                    "map": os.path.join( self.get_working_map_data_path(None), "%s.xml" % name ),
                    "dialogue": os.path.join( self.get_working_map_data_path(None), "dialogue", "%s.dialogue.xml" % name ),
                    "menu": os.path.join( self.get_working_map_data_path(None), "levelmenus", "%s.levelmenus.xml" % name )
                },
                options = {
                    "is-new": False
                },
                control_center = None # Obsolete parameter, I should remove it from the function definition!
            )

            # We don't want to run any kind of script on the map.  No onvisit, onbirth...
            # not even onload for now.  Maybe I'll change my mind later.

            # Here, though, we do want to load the map's memory.  Maybe an NPC has changed class, state, etc.
            m.load_memory(self, self.session)

            # Return the temporary map object
            return m

        else:
            return None


    # Get the path to a given map by its name
    def get_map_path_by_name(self, name):

        # Return full path
        return os.path.join( self.get_working_map_data_path(None), "%s.xml" % name )


    # Build all data for a given map (by name) on a given layer
    def build_map_on_layer_by_name(self, name, layer, game_mode, control_center, ignore_adjacent_maps = False):

        # If we want to ignore all adjacent maps, then I'm going to force a clear of
        # all foreground maps, then build only the given map on the foreground.
        if (ignore_adjacent_maps):

            # Clear foreground layer
            self.visible_maps[LAYER_FOREGROUND].clear()


        # By default, place the map according to the last universal coordinates
        if ( not ( name in self.visible_maps[layer] ) ):

            # Create a Map object
            self.visible_maps[layer][name] = self.create_map(
                name = name,
                x = self.map_data[layer][ name ].x,
                y = self.map_data[layer][ name ].y,
                options = {
                    "is-new": False
                },
                control_center = control_center
            )

            # Validate that we created the map
            if ( self.visible_maps[layer][name] ):

                # Convenience
                m = self.visible_maps[layer][name]


                # Load the map
                m.load(
                    filepaths = {
                        "map": os.path.join( self.get_working_map_data_path(None), "%s.xml" % name ),
                        "dialogue": os.path.join( self.get_working_map_data_path(None), "dialogue", "%s.dialogue.xml" % name ),
                        "menu": os.path.join( self.get_working_map_data_path(None), "levelmenus", "%s.levelmenus.xml" % name )
                    },
                    options = {
                        "is-new": False
                    },
                    control_center = control_center
                )

                # For level editor purposes (so it knows to simply overwrite...)
                m.saved = True


                # If we're in the game, then we should check for startup scripts, then
                # load memory and set the map as visited (for the worldmap).
                if (game_mode == MODE_GAME):

                    self.push_map_as_active(m)

                    # Run universal onload script first
                    self.run_script("global.map.onload", control_center)

                    # We always call an "onload" script, if such a script exists.
                    # onload scripts usually just flag some settings and things like that,
                    # so we want to run through all packets at once if possible...
                    m.run_script("onload", control_center, universe = self, execute_all = True)


                    # Does the map have an onbirth script, and is this the first time
                    # we've visited it?  If so, run it here...
                    if ( self.is_map_newborn(name) ):

                        # onbirth scripts usually just flag some settings and things like that,
                        # so we want to run through all packets at once if possible...
                        m.run_script("onbirth", control_center, universe = self, execute_all = True)


                    # Does this universe use map memory data?
                    if (not self.ignore_map_memory_files):

                        # Load memory for this map
                        m.load_memory(self, self.session)


                    # Run universal "map loaded" script
                    self.run_script("global.map.load.complete", control_center)


                    # Mark active map as "visited"
                    #self.set_map_as_visited(name) # Not here, I don't think.  Only in activate map, right?

                    # Mark this map as visible, it's definitely visible now
                    self.set_map_as_visible(name)

                    self.pop_pushed_active_map()


        # Set up an empty list to track potential fall regions.
        fall_regions = []

        # Assume all tiles below have a fall region, until we prove otherwise.
        # In the end, we'll have a list of only those specific tx coordinates leading to a fall region.
        tiles_in_fall_region = range( -1, self.map_data[layer][ name ].width + 1 )


        # Calculate the y-coordinate the map must have below the active map (flush alignment).
        y_below = self.map_data[layer][ name ].y + self.map_data[layer][ name ].height


        # Load in any maps adjacent to the currently active map,
        # provided that we haven't chosen to ignore adjacent maps.
        if ( (not ignore_adjacent_maps) and (name in self.adjacency_data[layer]) ):

            for map_name in self.adjacency_data[layer][name]:

                #log( "Let's load '%s'..." % map_name )

                # Load the map if it isn't already in the visible maps hash...
                if ( not (map_name in self.visible_maps[layer]) ):

                    # Create adjacent Map object
                    self.visible_maps[layer][map_name] = self.create_map(
                        name = map_name,
                        x = self.map_data[layer][map_name].x,
                        y = self.map_data[layer][map_name].y,
                        options = {
                            "is-new": False
                        },
                        control_center = control_center
                    )

                    # Validate map creation
                    if ( self.visible_maps[layer][map_name] ):

                        # Convenience
                        m2 = self.visible_maps[layer][map_name]


                        # Load the map
                        m2.load(
                            filepaths = {
                                "map": os.path.join( self.get_working_map_data_path(None), "%s.xml" % map_name ),
                                "dialogue": os.path.join( self.get_working_map_data_path(None), "dialogue", "%s.dialogue.xml" % map_name ),
                                "menu": os.path.join( self.get_working_map_data_path(None), "levelmenus", "%s.levelmenus.xml" % map_name )
                            },
                            options = {
                                "is-new": False
                            },
                            control_center = control_center
                        )

                        # For level editor purposes (so it knows to simply overwrite...)
                        m2.saved = True


                        # If we're in game, then we'll check the onbirth script for any adjacent map.
                        if (game_mode == MODE_GAME):

                            # Push the adjacent map as a faux active map
                            self.push_map_as_active(m2)# self.visible_maps[layer][map_name] )


                            # Run universal onload script
                            #self.run_script("global.map.onload", control_center)
                            #m2.import_script(
                            #    "global.map.onload",
                            #    self.get_script("global.map.onload")
                            #)
                            self.run_script("global.map.onload", control_center, execute_all = True)

                            # We always call an "onload" script, if such a script exists...
                            # onload scripts usually just flag some settings and things like that,
                            # so we want to run through all packets at once if possible...
                            m2.run_script("onload", control_center, universe = self, execute_all = True)


                            # Does the new map have an onbirth script, and is this the first time
                            # we've visited it?  If so, run it here...
                            if ( self.is_map_newborn(map_name) ):

                                # onbirth scripts usually just flag some settings and things like that,
                                # so we want to run through all packets at once if possible...
                                m2.run_script("onbirth", control_center, universe = self, execute_all = True)


                            # Does this universe use map memory data?
                            if (not self.ignore_map_memory_files):

                                # Load memory for perimeter map
                                m2.load_memory(self, self.session)


                            #m2.import_script(
                            #    "global.map.load.complete",
                            #    self.get_script("global.map.load.complete")
                            #)
                            self.run_script("global.map.load.complete", control_center, execute_all = True)


                            # Pop that map from the pushed map list; we've run all of its onbirth/onload script data, or all that we can without blocking.
                            self.pop_pushed_active_map()



                #???
                # Does this map sit flush below the new map?
                if (self.map_data[layer][map_name].y == y_below):

                    # Loop across the width of the map, noting that we don't
                    # need a fall region because this map is below it at that x-coordinate.
                    for tx in range( 0, self.map_data[layer][map_name].width ):

                        # On this tile in the map below, which tile does that represent
                        # on the main map we're building?
                        tx2 = (self.map_data[layer][map_name].x - self.map_data[layer][name].x) + tx

                        # If that is a valid tile (i.e. exists in the fall region tile index list),
                        # then we'll remove it.
                        if (tx2 in tiles_in_fall_region):

                            # Remove; this tile does not lead to a fall region.
                            tiles_in_fall_region.remove(tx2)


                # Make sure we mark this map as, at the least, "seen" (no longer under "fog of war")
                self.set_map_as_visible(map_name)


            # If we have any adjacency data, then lastly we'll build the bounds plane
            if (game_mode == MODE_GAME):

                # Note that we don't bother with this collision detection service while level editing
                self.visible_maps[layer][name].build_bounds_plane(self.visible_maps[layer])


            # Consolidate the fall region sections into as few rectangles as possible
            i = 0
            while ( i < len(tiles_in_fall_region) ):

                # Do we have another tile ahead to consider for consolidation?
                if ( i < len(tiles_in_fall_region) - 1 ):

                    # Assume width of 1
                    w = 1

                    # Consolidate as much as we can
                    while ( (i < len(tiles_in_fall_region) - 1) and (tiles_in_fall_region[i + 1] == (tiles_in_fall_region[i] + w)) ):

                        # Remove this next tile from the tiles candidate list
                        tiles_in_fall_region.pop(i + 1)

                        # Increase width
                        w += 1

                    # Add the consolidated rectangle fall region
                    fall_regions.append(
                        (tiles_in_fall_region[i], w)
                    )

                # If not, add a single-tile rectangle (we're at the end of the map)
                else:

                    # Single tile fall region
                    fall_regions.append(
                        (tiles_in_fall_region[i], 1)
                    )


                # Move to next possible tile
                i += 1


            # Set fall regions
            self.visible_maps[layer][name].set_fall_regions(fall_regions)
            logn( "universe fall-regions", "Fall regions for \"%s\" (from %s):  %s\n" % (name, "-", fall_regions) )


    # Remove a given map (by name) from a given layer
    def remove_map_on_layer_by_name(self, name, layer):

        # Validate that the map exists on that layer
        if ( name in self.visible_maps[layer] ):

            # Clear it, and return it just in case we want to do something with it...
            return self.visible_maps[layer].pop(name)


    # Precalculate adjacency data for each map...
    def calculate_adjacency_data_on_layer(self, layer):

        # Clear any existing data
        self.adjacency_data[layer].clear()

        # Loop through each map...
        for map_name in self.map_data[layer]:

            # Initialize perimeter collection
            self.adjacency_data[layer][map_name] = []


            # Get universal rectangle
            rMap = (self.map_data[layer][map_name].x * TILE_WIDTH, self.map_data[layer][map_name].y * TILE_HEIGHT, self.map_data[layer][map_name].width * TILE_WIDTH, self.map_data[layer][map_name].height * TILE_HEIGHT)

            # Pad the rectangle by the amount of perimeter scroll available...
            rMapPadded = offset_rect(rMap, x = -MAX_PERIMETER_SCROLL_X, y = -MAX_PERIMETER_SCROLL_Y, w = (2 * MAX_PERIMETER_SCROLL_X), h = (2 * MAX_PERIMETER_SCROLL_Y))


            # Small maps may not fill the entire screen, even with the added perimeter padding.  Thus, theoretically
            # a map 2 maps over could be visible from such a small map...
            if (rMapPadded[2] < SCREEN_WIDTH):

                # Pad each side by half of the total unused space
                pad_x = int( (SCREEN_WIDTH - rMapPadded[2]) / 2)

                # Pad the padded rect
                rMapPadded = offset_rect(rMapPadded, x = -pad_x, y = 0, w = (2 * pad_x), h = 0)

            # Same for y-axis...
            if (rMapPadded[3] < SCREEN_HEIGHT):

                # Pad the top/bottom
                pad_y = int( (SCREEN_HEIGHT - rMapPadded[3]) / 2)

                # Pad the padded rect
                rMapPadded = offset_rect(rMapPadded, x = 0, y = -pad_y, w = 0, h = (2 * pad_y))


            # For each map, check all other maps for adjacency determination...
            for perimeter_name in self.map_data[layer]:

                # Exclude the map we're building data for...
                if (perimeter_name != map_name):

                    # here, we're only going to care about the raw rectangle; we won't offset it in any way.
                    rPerimeter = (self.map_data[layer][perimeter_name].x * TILE_WIDTH, self.map_data[layer][perimeter_name].y * TILE_HEIGHT, self.map_data[layer][perimeter_name].width * TILE_WIDTH, self.map_data[layer][perimeter_name].height * TILE_HEIGHT)


                    # If the 2 rectangles overlap, then this will qualify as an adjacent perimeter map; we will want to load it for rendering when on the "map_name" map.
                    if (intersect(rMapPadded, rPerimeter)):

                        self.adjacency_data[layer][map_name].append(perimeter_name)


    # Discard any out of range map
    def discard_nonadjacent_maps(self):

        # Track which maps we'll discard
        trash_collection = []


        # Check all loaded maps.  Only do this for real-time rendered foreground maps
        for map_name in self.visible_maps[LAYER_FOREGROUND]:

            # Active or adjacent map?  Keep it, pass...
            if ( ( map_name == self.get_active_map().name ) or ( map_name in self.adjacency_data[LAYER_FOREGROUND][ self.get_active_map().name ] ) ):
                log( "Keeping '%s'..." % map_name )

            # Nope; we don't need this one anymore...
            else:
                log( "Discarding '%s!'" % map_name )

                # Queue it for removal so that we don't screw up our foreach loop
                trash_collection.append(map_name)


        # Now we can remove any offscreen map from the visible maps collection...
        for map_name in trash_collection:

            # Goodbye
            self.visible_maps[LAYER_FOREGROUND].pop(map_name)


        log( "Currently visible maps:  ", )
        for x in self.visible_maps[LAYER_FOREGROUND]:
            log( "%s ," % x, )
        log( " " )


    # Calculate parallax data for the foreground layer
    def calculate_parallax_data(self):

        # Only the foreground layer uses this
        layer = LAYER_FOREGROUND

        # Clear any existing data
        self.parallax_data[layer].clear()


        # Loop each map
        for map_name in self.map_data[layer]:

            # Initialize parallax data collection
            self.parallax_data[layer][map_name] = []


            # Convenience
            data = self.map_data[layer][map_name]


            # Begin by calculating this map's general bounds
            rMap = self.get_base_region_for_map_on_layer(map_name, layer)

            # Now we shall calculate the region in which the camera can scroll
            # (thus including the maximum perimeter wander).
            rPerimeter = self.get_camera_region_for_map_on_layer(map_name, layer)


            # Lastly, we shall calculate a rectangle that scales according
            # to the parallax layer's scroll factor.  (i.e. scale * n parallax pixels
            # will fit within n pixels on the foreground layer)
            rParallax = offset_rect(
                rPerimeter,
                w = int(rPerimeter[2] / BACKGROUND_MAP_PARALLAX_SCALE) - rPerimeter[2],
                h = int(rPerimeter[3] / BACKGROUND_MAP_PARALLAX_SCALE) - rPerimeter[3]
            )


            # Now the fun part!  We need to check each background map to
            # see which ones can potentially render while on this foreground level.
            for parallax_name in self.map_data[LAYER_BACKGROUND]:

                # Convenience
                parallax_data = self.map_data[LAYER_BACKGROUND][parallax_name]

                # Calculate the parallax offset based on the minimum (upper-left) position
                # of the perimeter region (camera range).
                (px, py) = (
                    int( abs(rPerimeter[0]) / BACKGROUND_MAP_PARALLAX_SCALE ) - abs(rPerimeter[0]),
                    int( abs(rPerimeter[1]) / BACKGROUND_MAP_PARALLAX_SCALE ) - abs(rPerimeter[1])
                )

                if ( rPerimeter[0] < 0 ):
                    px *= -1

                if ( rPerimeter[1] < 0 ):
                    py *= -1


                # Calculate the non-adjusted region for this parallax map, to scale...
                rNonadjusted = (
                    (parallax_data.x * TILE_WIDTH * BACKGROUND_MAP_SCALE),
                    (parallax_data.y * TILE_HEIGHT * BACKGROUND_MAP_SCALE),
                    (parallax_data.width * TILE_WIDTH * BACKGROUND_MAP_SCALE),
                    (parallax_data.height * TILE_HEIGHT * BACKGROUND_MAP_SCALE)
                )

                # Now adjust to account for parallax slide
                rAdjusted = offset_rect(
                    rNonadjusted,
                    x = -px,
                    y = -py
                )


                # At long last, we can check to see if this map could potentially render
                # while playing on the foreground map.
                if ( intersect(rAdjusted, rParallax) ):

                    # Track it!
                    self.parallax_data[layer][map_name].append(parallax_name)


    # Transition to a different part of the universe... a new map "name" at an optional spawn waypoint...
    def transition_to_map(self, name, waypoint_from = "", waypoint_to = "", control_center = None, save_memory = True, can_undo = True):

        # In the session, track where we're coming from and where we're going to...
        m = self.get_active_map()


        # If we're transitioning away from a linear level, then we're going to flatly assume
        # that we're transitioning to another linear level.
        ignore_adjacent_maps = ( m.get_type() == "linear" )


        # In case we loaded from a menu or something...
        if (can_undo):

            self.set_session_variable("app.transition.from.map", m.name)
            self.set_session_variable("app.transition.from.waypoint", waypoint_from)

            # Remember the player's location on the source map...
            player = m.get_entity_by_name("player1")

            if (player):

                self.set_session_variable("app.transition.from.player-x", "%d" % player.get_x() )
                self.set_session_variable("app.transition.from.player-y", "%d" % player.get_y() )


        #"""
        # Track our destination...
        self.set_session_variable("app.transition.to.map", name)
        self.set_session_variable("app.transition.to.waypoint", waypoint_to)
        #"""

        log2( "Transition to map:  %s" % name )

        #self.finalize_map_transition(control_center, save_memory)



        # Before we destroy the visible maps, let's keep track
        # of the player object's name...
        player_name = m.get_entity_by_name("player1").name

        # Save the memory of the current map, if requested...
        # (e.g. we do this when going from one room to another, but we don't do this if the player just died and is reloading a checkpoint,
        # or if they're loading a previously saved game while on a map)
        if (save_memory):

            m.save_memory(self)


        # Let's begin by clearing the visible (foreground) maps...
        self.visible_maps[LAYER_FOREGROUND].clear()



        # Now that we've established a new active map name and such,
        # let's set the new, destination map as active, building any relevant
        # map data thereof...
        log2( "Finalize transition to:  ", name )
        self.activate_map_on_layer_by_name( name, LAYER_FOREGROUND, control_center = control_center, ignore_adjacent_maps = ignore_adjacent_maps )


        # Assume we'll position the player at the last-known position in the session (perhaps from a save file)
        (spawnX, spawnY) = (
            int( self.get_session_variable("core.player1.x").get_value() ),
            int( self.get_session_variable("core.player1.y").get_value() )
        )


        # Now, try to get the destination waypoint
        trigger = self.get_active_map().get_trigger_by_name(waypoint_to)

        # Validate
        if (trigger):

            # We'll position the player on the new map at this located waypoint
            (spawnX, spawnY) = (
                trigger.get_rect(is_editor = False)[0],
                trigger.get_rect(is_editor = False)[1]
            )



        # Just in case, remove any player entity by the given name on the new map...
        self.visible_maps[LAYER_FOREGROUND][self.active_map_name].remove_entity_by_type_and_name(GENUS_PLAYER, player_name)

        # Create a player object on the new map and place it at the indicated spawn point..
        new_player = self.get_active_map().create_player().describe({
            "name": player_name,
            "genus": GENUS_PLAYER,
            "absolute-x": spawnX,
            "absolute-y": spawnY
        })

        # Now, add the player to the new map...
        self.visible_maps[LAYER_FOREGROUND][self.active_map_name].master_plane.entities[GENUS_PLAYER].append( new_player )


        # Get the newly-created player object
        player = self.get_active_map().get_entity_by_name(player_name)

        # Validate
        if (player):

            # Colorify the player by their saved color
            player.colorify(
                self.get_session_variable("core.player1.colors").get_value()
            )


            # The active map now has a player object.  What if, though, that player object
            # is stuck inside of the level (e.g. at the time they saved, they were in a hole they
            # had dug)?  In that case, we should place them at the "safe-spawn" waypoint, if possible.
            if ( self.get_active_map().master_plane.check_collision_in_rect( player.get_rect() ) ):

                # Can we get the waypoint "safe-spawn?"
                trigger = self.get_active_map().get_trigger_by_name("safe-spawn")


                # Yep, let's move the player now...
                if (trigger):

                    # Position the player at the predefined safe-spawn
                    player.position_at_waypoint(trigger)


        # Flag that we haven't processed any potential player death yet.  On death, we'll follow through with a menu creation
        self.set_session_variable("core.handled-local-death", "0")


        # Center the camera on the new map, immediately...
        self.center_camera_on_map(
            self.get_active_map()
        )


        log2( "**player status = %s\n" % player.status )

        # Fetch the window controller
        #window_controller = control_center.get_window_controller()

        # Unhook from it
        #window_controller.unhook(self)


        # App fade in as we arrive on the new map
        #window_controller.fade_in()


    def undo_last_map_transition(self, control_center, save_memory = True):

        self.transition_to_map(
            name = self.get_session_variable("app.transition.from.map").get_value(),
            waypoint_to = self.get_session_variable("app.transition.from.waypoint").get_value(),
            save_memory = save_memory,
            can_undo = False,
            control_center = control_center
        )

        # Get the player's current coordinates
        (spawnX, spawnY) = (
            self.get_local_player().get_x(),
            self.get_local_player().get_y()
        )

        # Remember the player's new position as they (return to the previous map)   #enter the new map...
        self.set_session_variable("core.player1.x", "%d" % spawnX)
        self.set_session_variable("core.player1.y", "%d" % spawnY)

        # Autosave on new map
        self.commit_autosave(
            control_center,
            universe = self
        )


    # Count the amount of (collectable) gold that exists in the entire universe (across all playable (i.e. foreground) maps)
    def calculate_universal_gold_total(self):

        # Only foreground maps have (collectable) gold on them
        return sum(self.map_data[LAYER_FOREGROUND][map_name].gold_count for map_name in self.map_data[LAYER_FOREGROUND])


    # Get the list of level xp requirement hashes
    def get_level_xp_requirements(self):

        # Return
        return self.level_xp_requirements


    def get_unlocked_skill_names(self):

        results = []

        for skill in ACTIVE_SKILL_LIST:

            level = int( self.get_session_variable("core.skills.%s" % skill).get_value() )

            # Is it unlocked?
            if (level > 0):

                results.append(skill)

        return results

    def assign_skill_to_slot(self, skill, slot):

        # Validate
        if (skill in ACTIVE_SKILL_LIST):

            self.get_session_variable("core.player1.skill%d" % slot).set_value(skill)


    # Check to see if a given skill is equipped
    def is_skill_equipped(self, skill):

        # Check each slot
        for slot in range(1, MAX_SKILL_SLOTS + 1):

            # Skill assigned to this slot?
            if ( self.get_session_variable("core.player1.skill%d" % slot).get_value() == skill ):

                # Yep, it's equipped
                return True


        # Not equipped
        return False


    def get_skill_level(self, skill):

        if (skill in SKILL_LIST):

            return int( self.get_session_variable("core.skills.%s" % skill).get_value() )


    # Count how many gold pieces the player has collected within the universe
    # Optionally specify a class of map to consider.
    def count_collected_gold_pieces(self, map_type = "*"):

        # Tally
        count = 0

        # Loop foreground maps
        for name in self.map_data[LAYER_FOREGROUND]:

            # Class matches?
            if ( self.map_data[LAYER_FOREGROUND][name].has_class(map_type) ):

                # Deduce how much we have collected
                count += (self.map_data[LAYER_FOREGROUND][name].gold_count - self.map_data[LAYER_FOREGROUND][name].gold_remaining)

        # Return total
        return count


    # Count how many gold pieces exist within the universe.
    # Optionally specify a class of map to consider.
    def count_gold_pieces(self, map_type = "*"):

        # Tally
        count = 0

        # Loop foreground maps
        for name in self.map_data[LAYER_FOREGROUND]:

            # Class matches?
            if ( self.map_data[LAYER_FOREGROUND][name].has_class(map_type) ):

                # Count possible
                count += self.map_data[LAYER_FOREGROUND][name].gold_count

        # Return total
        return count


    # Count how many quests we've completed in this universe
    def count_completed_quests(self):

        # Grab length of matching quests
        return len( self.get_completed_quests() )


    # Count how many quests exist wtihin the universe
    def count_quests(self):

        # Simple length check
        return len( self.get_quests() )


    # Track a newly acquired quest by its name (whether the quest is in-progress, complete, or failed doesn't matter)
    def track_quest_by_name(self, name):

        # Don't add duplicates
        if ( not (name in self.active_quests_by_name) ):

            # Track
            self.active_quests_by_name.append(name)


    # Return this universe's quests
    def get_quests(self):

        return self.quests


    def get_all_quests(self):

        return self.quests


    def get_active_quests(self):

        # Track matches
        results = []

        # Loop quests
        for quest in self.quests:

            # Active?
            if ( (quest.active) and (quest.status == QUEST_STATUS_IN_PROGRESS) ):

                # Track
                results.append(quest)

        # Sort results by order of acquisition
        results = sorted(
            results,
            key = lambda o, z = self.active_quests_by_name: z.index(o) if (o in z) else len(z)
        )

        # Return matches
        return results


    def get_completed_quests(self):

        # Track matches
        results = []

        # Loop quests
        for quest in self.quests:

            # Complete?
            if (quest.status == QUEST_STATUS_COMPLETE):

                # Track
                results.append(quest)

        # Sort results by order of acquisition
        results = sorted(
            results,
            key = lambda o, z = self.active_quests_by_name: z.index(o) if (o in z) else len(z)
        )

        # Return matches
        return results


    # Get all finished quests.  This includes both completed and failed quests.
    def get_finished_quests(self):

        # Track matches
        results = []

        # Loop quests
        for quest in self.quests:

            # Completed or failed?
            if ( quest.status in (QUEST_STATUS_COMPLETE, QUEST_STATUS_FAILED) ):

                # Track
                results.append(quest)

        logn( "universe quests debug", "active quests:  %s" % self.active_quests_by_name )

        # Sort results by order of acquisition
        results = sorted(
            results,
            key = lambda o, z = self.active_quests_by_name: z.index( o.get_name() ) if ( o.get_name() in z ) else len(z)
        )

        # Return matches
        return results


    # Scripts need this for flagging individual quests
    def get_quest_by_name(self, name):

        for quest in self.quests:

            if (quest.name == name):
                return quest

        # Couldn't find it...
        return None


    # Create a new inventory item
    def create_item(self):

        # Base
        return InventoryItem()


    # Get item template
    def get_item_by_name(self, name):

        for item in self.items:

            if (item.name == name):
                return item

        return None


    # Get a currently equipped item, by name
    def get_equipped_item_by_name(self, name):

        for item in self.equipped_inventory:

            if (item.name == name):
                return item

        return None


    # Get an acquired item, by name
    def get_acquired_item_by_name(self, name):

        # Check our inventory, to date
        for item in self.acquired_inventory:

            # Match!
            if ( name == item.get_name() ):

                # Return the item object
                return item

        # 404
        return None


    def get_acquired_item_names(self, sorting_method = "alpha", descending = False):

        # Track sorted results...
        results = []

        # Populate with the item names first...
        for item in self.acquired_inventory:

            results.append( (item.title, item.name) )


        # Alpha sort?
        if (sorting_method == "alpha"):

            #results.sort(key = lambda x: x.name, reverse = descending)
            results.sort()

            if (descending):

                results.reverse()

        # Order of acquisition?
        elif (sorting_method == "order-of-acquisition"):

            # The acquired inventory by default sorts in order of acquisition.
            # We might still want descending order, though...
            if (descending):

                results.reverse()


        single_results = []

        for (title, name) in results:

            single_results.append(name)


        return single_results

    def get_unacquired_item_names(self, quality_range = None, warehouse_collection = [], blacklist = []):

        results = []

        # Check all items...
        for item in self.items:

            # Skip blacklisted items right away...
            if (not (item.name in blacklist)):

                if (not self.is_item_acquired(item.name)):

                    # Make sure the item is stocked by one of the provided warehouses
                    if ( any(e in warehouse_collection for e in item.warehouses) ):

                        # Do we care about quality?
                        if (quality_range):

                            if (item.quality in quality_range):

                                results.append(item.name)


                        # No... we'll take anything...
                        else:

                            results.append(item.name)

        return results

    def fetch_n_virgin_item_names(self, n, min_quality = 0, max_quality = 100, warehouse_collection = [], blacklist = []):

        results = []


        # Which items have not yet been acquired?
        unacquired_item_names = self.get_unacquired_item_names(quality_range = range(min_quality, max_quality + 1), warehouse_collection = warehouse_collection, blacklist = blacklist)

        log( "Unacquired items:\n", unacquired_item_names )


        # Of that list of items, let's take "n" at random...
        while ( (len(results) < n) and (len(unacquired_item_names) > 0) ):

            # Try to get a new item at random...
            index = random.randint(0, (len(unacquired_item_names) - 1))

            # Add the item...
            results.append( unacquired_item_names.pop(index) )


        return results


    # Add an item to the acquired inventory
    def add_item_to_acquired_inventory(self, item):

        # Append
        self.acquired_inventory.append(item)


    # Acquire a new item.  First, create the item; second, randomly select some number of upgrades
    # from the candidate pools; lastly, add those upgrades to the item and add the item to inventory.
    def acquire_item_by_name(self, name):

        # Find the base item
        item = self.get_item_by_name(name)

        # Validate
        if (item):

            # Clone the item
            new_item = item.clone()


            # Prepare a list of possible upgrades
            upgrades = []

            # Loop through all possible pools
            for name in new_item.available_upgrade_pools_by_name:

                # Query the pool
                upgrade_pool = self.get_upgrade_pool_by_name(name)

                # Validate
                if (upgrade_pool):

                    # Extend upgrade candidates with all upgrades in this pool
                    upgrades.extend(
                        upgrade_pool.get_upgrades()
                    )


            logn( "universe item debug", "upgrade pools:  ", new_item.available_upgrade_pools_by_name )

            # Now we shall select 2 upgrades at random from the candidates
            for i in range(0, 2):

                # Assuming we have any upgrade available...
                if ( len(upgrades) > 0 ):

                    # Determine range
                    (a, b) = ( 0, len(upgrades) - 1 )

                    # Select an upgrade at random
                    pos = random.randint(a, b)

                    # Remove that upgrade from the list
                    upgrade = upgrades.pop(pos)

                    # Clone it into the available upgrades for the new item
                    new_item.add_available_upgrade(
                        upgrade.clone()
                    )


            # Lastly, add the new item to the acquired inventory list
            self.acquired_inventory.append(new_item)


            # Success
            return True

        # Couldn't validate
        else:

            return False


    def remove_item_from_inventory(self, name):

        i = 0

        # Find the item by its name in the acquired inventory list
        while (i < len(self.acquired_inventory)):

            # Match?  Remove it!
            if (self.acquired_inventory[i].name == name):

                self.acquired_inventory.pop(i)

            # Keep looping
            else:

                i += 1

        i = 0

        # Find the item by its name in the equipped inventory list.
        # If we had it equipped, we must "unequip" it.
        while ( i < len(self.equipped_inventory) ):

            # Match?
            if ( self.equipped_inventory[i].name == name ):

                # Remove from equipped inventory
                self.equipped_inventory.pop(i)

            # Loop
            else:
                i += 1


    # Get an upgrade pool, by name
    def get_upgrade_pool_by_name(self, name):

        # Loop
        for upgrade_pool in self.upgrade_pools:

            # Match?
            if (upgrade_pool.name == name):

                # Good
                return upgrade_pool

        # 404
        return None


    def is_item_acquired(self, name):

        for item in self.acquired_inventory:

            if (item.name == name):

                return True

        return False


    def is_item_equipped(self, name):

        for item in self.equipped_inventory:

            if (item.name == name):

                return True

        return False


    # Get all acquired items
    def get_acquired_items(self):

        # Here!
        return self.acquired_inventory


    # Get all equipped items
    def get_equipped_items(self):

        return self.equipped_inventory


    # Save the calculation for a given item result (e.g. player speed, enemy speed, etc.)
    def cache_item_attribute_result(self, name, value):

        # Simple
        self.item_attribute_result_cache[name] = value


    # Invalidate a given item attribute calculate result
    def invalidate_item_attribute_result(self, name):

        # Validate key
        if (name in self.item_attribute_result_cache):

            # Clear
            self.item_attribute_result_cache.pop(name)


    # Check for a previously cached item attribute result
    def get_cached_item_attribute_result(self, name):

        # Previously cached?
        if (name in self.item_attribute_result_cache):

            # Return it
            return self.item_attribute_result_cache[name]

        # Not found
        else:

            return None


    # Clear the item attribute result cache (perhaps a timer has expired and we want fresh data)
    def clear_item_attribute_result_cache(self):

        # Reset the hash
        self.item_attribute_result_cache.clear()


    # Equip an item (actually a clone of the given item)
    def equip_item_by_name(self, name):

        # Make sure we're not already wearing it...
        if ( not self.is_item_equipped(name) ):

            # Create a clone of the base item first.  We need to do this
            # because we're going to modify the item object to include
            # any upgrade the player has purchased, and we don't want to
            # modify the core object itself (i.e. the "blueprint").
            # Also note that we fetch the acquired item, not the base item;
            # only the acquired item contains committed upgrade information.
            item = self.get_acquired_item_by_name(name)

            # Validate
            if (item):

                # Clone item to preserve original reference
                item = item.clone()

                # The item, when equipped, should include the attributes
                # of any purchased upgrade.
                item.inherit_committed_upgrades()

                # Equip the cloned item!
                self.equipped_inventory.append(item)

            else:
                logn( "item error", "Aborting:  Item '%s' does not exist!" % name )
                #sys.exit()


    def unequip_item_by_name(self, name):

        i = 0

        while (i < len(self.equipped_inventory)):

            if (self.equipped_inventory[i].name == name):
                self.equipped_inventory.pop(i)

            else:
                i += 1


    # Fading away?
    def is_fading(self):

        return ( self.alpha_controller.get_target() == 0 )


    # Faded away?
    def is_gone(self):

        return ( not self.alpha_controller.is_visible() )


    # Set fade mode
    def set_fade_mode(self, mode):

        self.fade_mode = mode


    def fade_out(self, on_complete = ""):

        self.alpha_controller.dismiss(
            target = 0.0,
            on_complete = on_complete
        )


    def fade_in(self, on_complete = ""):

        self.alpha_controller.summon(
            target = 1.0,
            on_complete = on_complete
        )


    # Get script data for a given script, by name.
    # Return None if the script does not exist.
    def get_script(self, name):

        # Validate
        if (name in self.scripts):

            # Return raw script code
            return self.scripts[name]

        # Not found
        else:
            return None


    # Run a universe (global) script.
    # This function simply takes the given script and feeds it to the map's event controller, for now.
    def run_script(self, name, control_center, execute_all = False):

        # Validate name
        if (name in self.scripts):

            # Get active map
            m = self.get_active_map()
            logn( "script universe", "Debug mes:  Run '%s' on '%s'\n" % (name, m.get_name()) )

            # Validate
            if (m):

                # Do we need to compile the universe script?
                if ( not (name in self.compiled_scripts) ):

                    # Compile on-the-fly
                    self.compiled_scripts[name] = Script( self.scripts[name] )


                # Get the map's event controller
                event_controller = m.get_event_controller()

                # Load compiled script
                event_controller.load(
                    copy.deepcopy(self.compiled_scripts[name])
                )

                # Loop?
                if (execute_all):

                    event_controller.loop(control_center, universe = self)


    # Execute a script immediately, by name.
    # Any blocking call will fail!
    def execute_script(self, name, control_center, universe, execute_all = False):

        # Validate
        if (name in self.scripts):

            # Do we need to compile this script?
            if ( not (name in self.compiled_scripts) ):

                # Compile on-the-fly
                self.compiled_scripts[name] = Script( self.scripts[name] )


            # Create a new, temporary event controller
            event_controller = control_center.create_event_controller()

            # Load the compiled script
            event_controller.load( self.compiled_scripts[name] )

            # Run for as long as we can
            event_controller.loop(control_center, universe)


    def process(self, widget_dispatcher):

        # Events that arise from handling various universe objects
        results = EventQueue()


    # Process logic for the level editor (paint tiles, etc.)
    def process_editor_input_and_logic(self, editor_input, control_center):

        # Fetch the input controller;
        input_controller = control_center.get_input_controller()

        # and, obviously, the editor controller!;
        editor_controller = control_center.get_editor_controller()

        # also, the GUI manager
        gui_manager = control_center.get_gui_manager()

        # and the (G)UI responder...
        ui_responder = control_center.get_ui_responder()



        # Let's begin by doing generic editor controller processing
        editor_controller.process()


        # Fetch keypress data
        keypresses = input_controller.get_keypresses()


        # Check for clutch-drag
        if ( editor_input["clutching"] ):

            # Move by mouse change
            scalar = 1

            # Or, 3x mouse change while holding shift?
            if ( keypresses[K_LSHIFT] ):

                # Super-fast clutch dragging!
                scalar = 3

            # Move camera
            self.camera.x -= scalar * editor_input["mdx"]
            self.camera.y -= scalar * editor_input["mdy"]


        # Current zoom scalar
        zoom = editor_controller.zoom_controller.get_interval()

        # Stash current camera position
        (cameraX, cameraY) = (
            int(zoom * self.camera.x),
            int(zoom * self.camera.y)
        )

        """
        # When "zoomed" (showing only background), adjust the camera by scale
        if ( editor_controller.layer_visibility[LAYER_FOREGROUND] == False ):

            # Scale camera position
            (cameraX, cameraY) = (
                int(cameraX / BACKGROUND_MAP_SCALE),
                int(cameraY / BACKGROUND_MAP_SCALE)
            )
        """


        # Always remember the last mouse position
        editor_controller.mouse.x = editor_input["mx"]
        editor_controller.mouse.y = editor_input["my"]

        # Also remember last camera position
        editor_controller.camera.x = cameraX
        editor_controller.camera.y = cameraY


        # Check for right-click action...
        if ( editor_input["right-clicked"] ):

            # Mouse position (in relative screen coordinates)
            (x, y) = pygame.mouse.get_pos()
            mr = (x, y, 1, 1)


            # Stop dragging anything we might have been dragging
            editor_controller.drag.object_type = ""


            # Did we find something special to right click on?  (Context-sensitive, e.g. maps, planes, triggers, etc.)
            found_item = False

            # Track whether or not the mouse intersects the active map
            editing_active_map = False

            # Store whichever right-click dialog we create in here
            dialog = None


            # Active map, if/a
            if ( self.active_map_name in self.visible_maps[ editor_controller.active_layer ] ):

                # Get map
                m = self.visible_maps[ editor_controller.active_layer ][ self.active_map_name ]

                # Convenience
                layer = m.layer

                # Calculate zoom-adjusted scale ratio, as well as parallax ratio
                scale = zoom * SCALE_BY_LAYER[layer]
                parallax = 1 * PARALLAX_BY_LAYER[layer]


                # Convenience
                (mx, my) = (
                    editor_input["mx"],
                    editor_input["my"]
                )

                # Get the local screen render region for the active map
                rRender = self.get_render_region_for_map_on_layer(self.active_map_name, editor_controller.active_layer, scale = scale, parallax = parallax, zoom = zoom)

                logn( "universe debug", "**", m.name, rRender, mr, (scale, parallax) )

                # Track whether or not the mouse intersects with the render area of the active map
                editing_active_map = intersect(rRender, mr)


                # Tile coordinates we right-clicked on
                (tx, ty) = (
                    int( (mx - rRender[0]) / (scale * TILE_WIDTH) ),
                    int( (my - rRender[1]) / (scale * TILE_HEIGHT) )
                )

                # Track last mouse position data on the current map
                editor_controller.mouse.rightclick.x = mx
                editor_controller.mouse.rightclick.y = my

                editor_controller.mouse.rightclick.tx = tx
                editor_controller.mouse.rightclick.ty = ty


                # Check triggers...
                for t in m.triggers:

                    r = t.get_rect( is_editor = True )
                    r = offset_rect(r, rRender[0], rRender[1])#-cameraX + (m.x * TILE_WIDTH), -cameraY + (m.y * TILE_HEIGHT))

                    if (intersect(r, mr)):

                        if (not found_item):

                            found_item = True
                            editor_controller.mouse.rightclick.object_reference = t

                            dialog = gui_manager.get_widget_by_name("rk.triggers")

                # Check entities...
                for genus in m.master_plane.entities:

                    for entity in m.master_plane.entities[genus]:

                        r = entity.get_scaled_rect(scale = scale)
                        #r = offset_rect(r, -cameraX + (m.x * TILE_WIDTH), -cameraY + (m.y * TILE_HEIGHT))
                        r = offset_rect(r, rRender[0], rRender[1])

                        if (intersect(r, mr)):

                            if (not found_item):

                                found_item = True
                                editor_controller.mouse.rightclick.object_reference = entity

                                dialog = gui_manager.get_widget_by_name("rk.entities")


                # Check planes... top-left corner only...
                for plane in m.planes:

                    r = (m.x * TILE_WIDTH, m.y * TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT)

                    r = offset_rect(r, (plane.x * TILE_WIDTH), (plane.y * TILE_HEIGHT))
                    r = offset_rect(r, -cameraX, -cameraY)

                    # Calculate the local screen rendering region for this map
                    rRender = self.get_render_region_for_map_on_layer(m.name, editor_controller.active_layer, scale = scale, parallax = parallax, zoom = zoom)

                    # Offset by the plane's location (accounting for zoom level and scale)
                    rRender = offset_rect(
                        rRender,
                        x = (scale * TILE_WIDTH) * plane.x,
                        y = (scale * TILE_HEIGHT) * plane.y
                    )

                    rCorner = (
                        rRender[0],
                        rRender[1],
                        int(scale * TILE_WIDTH),
                        int(scale * TILE_HEIGHT)
                    )

                    if (intersect(rCorner, mr)):

                        if (not found_item):

                            found_item = True
                            editor_controller.mouse.rightclick.object_reference = plane

                            dialog = gui_manager.get_widget_by_name("rk.planes")

                            log2( plane )


            # Check all maps on the active layer.  Clicking on the top-left corner
            # of a map gives us a map menu (move map, select map, etc.)
            for key in self.visible_maps[ editor_controller.active_layer ]:

                # Convenience
                m = self.visible_maps[ editor_controller.active_layer ][ key ]

                # Calculate zoom-adjusted scale ratio, as well as parallax ratio
                scale = zoom * SCALE_BY_LAYER[editor_controller.active_layer]
                parallax = 1 * PARALLAX_BY_LAYER[editor_controller.active_layer]


                # Convenience
                (mx, my) = (
                    editor_input["mx"],
                    editor_input["my"]
                )

                # Absolute active map world position
                (map_x, map_y) = (
                    int(scale * m.x * TILE_WIDTH),
                    int(scale * m.y * TILE_HEIGHT)
                )

                # Retrieve parallax offsets at the given camera position
                (px, py) = self.camera.get_parallax_offsets_at_location(cameraX, cameraY, parallax = parallax)

                # Calculate the local screen rendering region for this map
                rRender = self.get_render_region_for_map_on_layer(key, editor_controller.active_layer, scale = scale, parallax = parallax, zoom = zoom)

                # We actually only want the upper-left corner of the map, the first tile...
                rCorner = (
                    rRender[0],
                    rRender[1],
                    int(scale * TILE_WIDTH),
                    int(scale * TILE_HEIGHT)
                )

                if (intersect(rCorner, mr)):

                    if (not found_item):

                        found_item = True
                        editor_controller.mouse.rightclick.object_reference = self.visible_maps[ editor_controller.active_layer ][key]

                        dialog = gui_manager.get_widget_by_name("rk.maps")


            # No item found?  Show a generic dialog, then...
            if (not found_item):

                # Are we actively editing the active map?
                if (editing_active_map):

                    # If so, show a generic right-click dialog for map editing
                    dialog = gui_manager.get_widget_by_name("rk.generic")

                # If not, we'll default to the "offmap" right-click dialog
                else:

                    # Show a very generic level editor right click dialog
                    dialog = gui_manager.get_widget_by_name("rk.offmap")



            # Did we decide we need to display a right-click dialog?
            if (dialog):

                (x, y) = pygame.mouse.get_pos()

                if (x >= (540)):
                    x -= 100

                if (y >= (400)):
                    y -= 100

                # Position the dialog where the user clicked
                dialog.x = x
                dialog.y = y

                if (dialog.alpha_controller.get_interval() > 0):
                    dialog.hide()

                else:

                    # Hide any right-click dialog
                    for key in ("rk.triggers", "rk.entities", "rk.maps", "rk.planes", "rk.script-tree", "rk.generic", "rk.offmap"):

                        dialog2 = gui_manager.get_widget_by_name(key)

                        if (dialog2):
                            dialog2.hide()

                    dialog.alpha_controller.configure({
                        "interval": 0,
                        "target": 0.9
                    })

                    dialog.show()
                    dialog.focus()
                    dialog.invalidate_cached_metrics()
                    #print dialog


        # Define screen camera position
        r = (cameraX, cameraY, SCREEN_WIDTH, SCREEN_HEIGHT)

        m = self.get_active_map()
        # Get active map if it's on the current layer, move it around, whatever
        if (m):#self.active_map_name in self.visible_maps[ editor_controller.active_layer ] ):

            # Convenience
            (mx, my) = (
                editor_input["mx"],
                editor_input["my"]
            )

            # Process...
            (raw_mx, raw_my) = (
                (cameraX + editor_input["mx"]),
                (cameraY + editor_input["my"])
            )

            (map_x, map_y) = (
                (m.x * TILE_WIDTH),
                (m.y * TILE_HEIGHT)
            )

            (tx, ty) = (
                int( (raw_mx - map_x) / TILE_WIDTH ),
                int( (raw_my - map_y) / TILE_HEIGHT )
            )

            # Convenience
            layer = m.layer

            # Calculate zoom-adjusted scale for this layer, then calculate parallax ratio
            scale = zoom * SCALE_BY_LAYER[layer]
            parallax = 1 * PARALLAX_BY_LAYER[layer]

            # Grab the active map's local screen render region
            rRender = self.get_render_region_for_map_on_layer(self.active_map_name, editor_controller.active_layer, scale = scale, parallax = parallax, zoom = zoom)

            # Based on the render region and the mouse position, along with current scale, calculate the currently active tile index (tx, ty)
            (tx, ty) = (
                int( (mx - rRender[0]) / (scale * TILE_WIDTH) ),
                int( (my - rRender[1]) / (scale * TILE_HEIGHT) )
            )

            # Must offset by -1 for negative values
            if (mx < rRender[0]):
                tx -= 1

            # Offset for y axis as well
            if (my < rRender[1]):
                ty -= 1


            # Inject current tile coordinates into editor input (hacky)
            editor_controller.mouse.tx = tx
            editor_controller.mouse.ty = ty
            #editor_input["mouse-tx"] = tx
            #editor_input["mouse-ty"] = ty


            # We might have disabled this while selecting a tile...
            if ( (not pygame.mouse.get_pressed()[0]) and (not editor_controller.selecting_tile) ):

                # Allow tile / entity painting
                editor_controller.can_paint = True


            # Process editor input for the active map
            m.handle_editor_input(editor_input, control_center)


            # If we're holding anything, let's update its location...
            if (editor_controller.drag.object_type != ""):

                # Disable drag while holding left control key (?)
                if ( not pygame.key.get_pressed()[K_LCTRL] ):

                    if (editor_controller.drag.object_type == "trigger"):

                        t = editor_controller.drag.object_reference

                        t.x = tx
                        t.y = ty

                    elif (editor_controller.drag.object_type == "entity"):

                        entity = editor_controller.drag.object_reference

                        entity.x = tx * TILE_WIDTH
                        entity.y = ty * TILE_HEIGHT

                    elif (editor_controller.drag.object_type == "plane"):

                        plane = editor_controller.drag.object_reference

                        plane.x = tx
                        plane.y = ty

                    elif (editor_controller.drag.object_type == "map"):

                        m = editor_controller.drag.object_reference

                        m.x = int(raw_mx / TILE_WIDTH)
                        m.y = int(raw_my / TILE_HEIGHT)

                        # If we're moving a background map while viewing the foreground,
                        # then adjust for background map scale.
                        if ( (editor_controller.active_layer == LAYER_BACKGROUND) ):#and (editor_controller.layer_visibility[LAYER_FOREGROUND]) ):

                            # Get parallax ratio
                            parallax = PARALLAX_BY_LAYER[editor_controller.active_layer]

                            # Get scale ratio
                            scale = SCALE_BY_LAYER[editor_controller.active_layer]


                            # First we must adjusted for the size scale
                            (adjustedX, adjustedY) = (
                                (raw_mx / scale),
                                (raw_my / scale)
                            )

                            # We must also factor in the parallax for the (adjusted) camera location
                            (px, py) = self.camera.get_parallax_offsets_at_location( (cameraX / scale), (cameraY / scale), parallax = parallax)

                            # Adjust again
                            (adjustedX, adjustedY) = (
                                adjustedX - px,
                                adjustedY - py
                            )


                            # Now apply the final location calculation
                            m.x = int(adjustedX / TILE_WIDTH)
                            m.y = int(adjustedY / TILE_HEIGHT)


                        # We need to update the map data for this map in real-time, as we drag it around...
                        self.map_data[m.layer][m.name].configure({
                            "x": m.x,
                            "y": m.y
                        })


                # If we left-click, we drop what we're holding...
                if ( editor_input["left-clicked"]):

                    # Set that we're not dragging any object type.  Anything we were dragging
                    # will become "stuck" (i.e. set permanently) at the position we last dragged it to...
                    editor_controller.drag.object_type = ""


    # Process logic for the game itself (character movement, etc.)
    def process_game_logic(self, control_center):

        # Events that result from anything we do here
        results = EventQueue()


        # Don't do ANYTHING if the network controller has a global lock
        if ( not control_center.get_network_controller().is_global_locked() ):

            # Before we get to business, let's handle alpha and stuff
            results.append(
                self.alpha_controller.process()
            )


            # Process the timer controller
            if ( not self.is_paused() ):

                results.append(
                    self.timer_controller.process()
                )


            # Also process the simple hslide controller
            #results.append(
            #    self.hslide_controller.process()
            #)


            # Get active map
            m = self.get_active_map()

            # Local player id?
            player_id = int( self.get_session_variable("core.player-id").get_value() )


            # Focus on the local player (without zap)
            m.center_camera_on_entity_by_name(self.camera, "player%d" % player_id, zap = False)


            # If we're not in a cutscene, then we should make sure to center the camera
            if ( m.get_status() != STATUS_CUTSCENE ):

                # Assume default camera speeds...
                (camera_speed_x, camera_speed_y) = (CAMERA_SPEED, CAMERA_SPEED)

                # When panning 2 directions at once, I want to pan in an even diagonal line...
                if ( (self.camera.x != self.camera.target_x) and (self.camera.y != self.camera.target_y) ):

                    slope = float(self.camera.target_y - self.camera.y) / float(self.camera.target_x - self.camera.x)

                    camera_speed_y = abs(slope * camera_speed_x)


                self.camera.pan(camera_speed_x, camera_speed_y)


            # Process camera (mostly just checking for dirty status)
            self.camera.process(control_center)


            # Define screen camera position
            rCamera = ( int(self.camera.x), int(self.camera.y), SCREEN_WIDTH, SCREEN_HEIGHT)


            # Should we try to discard offscreen maps?
            if (self.discard_offscreen_maps_on_camera_shift_completion):

                # When the camera reaches its pan destination, we'll remove offscreen maps.
                # We know that when the camera is at its destination, it's guaranteed to be
                # within the active level (+/- max perimeter pan values).
                if ( (rCamera[0] == self.camera.target_x) and (rCamera[1] == self.camera.target_y) ):

                    # Discard any nonadjacent map
                    self.discard_nonadjacent_maps()

                    # Disable flag; we're done with the work for now.
                    self.discard_offscreen_maps_on_camera_shift_completion = False

            # If the prerender is pending (i..e waiting for the camera shift to finish),
            # then let's see if we can yet set it to ready.
            if (self.prerender_status == PRERENDER_STATUS_PENDING):

                # When the camera finishes moving to the new map, we can prerender the
                # parallax data to a scratch pad.
                if ( (rCamera[0] == self.camera.target_x) and (rCamera[1] == self.camera.target_y) ):

                    # Update flag to ready (for the .draw_game function).
                    self.prerender_status = PRERENDER_STATUS_READY


            # If we've previously completed a prerender, we'll still need to check
            # the camera; if it's become "dirty," then we need to redo the prerender.
            elif (self.prerender_status == PRERENDER_STATUS_DONE):

                # Dirty camera has exceeded the available prerender data bounds
                if ( self.camera.is_dirty() ):

                    # So, we need to update the parallax scratch pad with freshly prerendered (graphic) data
                    self.prerender_status = PRERENDER_STATUS_READY

                    log2( "Recalculating prerender data" )



            # Stupid GIFs don't network!
            if ( self.get_session_variable("core.is-gif").get_value() == "0" ):

                # Fetch the network controller
                network_controller = control_center.get_network_controller()

                # Handle
                localization_controller = control_center.get_localization_controller()


                # Check netplay messages here???
                network_controller.process(control_center, universe = self)


                # Fetch next queued network command (i.e. message)
                command = network_controller.get_next_command()

                # Loop all
                while (command):

                    #log( "Received command:  ", command )

                    # Process command
                    self.process_network_command(command, control_center)

                    # Loop
                    command = network_controller.get_next_command()


                # The server should monitor for level victory / failure
                if ( network_controller.get_status() == NET_STATUS_SERVER ):

                    # Only check for victory / failure while the game remains in progress
                    if ( self.get_session_variable("net.game-in-progress").get_value() == "1" ):

                        # Level complete?  (Collected all gold?)
                        if ( self.get_active_map().remaining_gold_count() == 0 ):

                            # First, flag the game as no longer in progress
                            self.set_session_variable("net.game-in-progress", "0")


                            # Save linear progress data (mark as complete, best time, etc.)
                            self.save_linear_progress(control_center, universe = self)


                            # Add a "level complete" newsfeeder item
                            control_center.get_window_controller().get_newsfeeder().post({
                                "type": NEWS_NET_LEVEL_COMPLETE,
                                "title": localization_controller.get_label("level-complete:label"),
                                "content": localization_controller.get_label("moving-to-next-level:label")
                            })


                            # Fetch the window controller
                            window_controller = control_center.get_window_controller()

                            # Hook into the window controller to receive a forwarded event
                            window_controller.hook(self)


                            # Set a brief delay on the window controller
                            window_controller.delay(NET_TRANSITION_DELAY)

                            # Call for an app-level fade once that delay completes
                            window_controller.fade_out(
                                on_complete = "fwd.net.transition.finalize"
                            )


                            # Which level is next?
                            next_map_name = self.get_active_map().get_param("next-map")


                            # Validate that such a map exists!
                            if ( not (next_map_name in self.map_data[LAYER_FOREGROUND]) ):

                                # If the map does not exist, we're going to reload the same map over and over.
                                next_map_name = self.get_active_map().get_name()
                                log2( "Warning:  No 'next' nevel specified for '%s'" % self.get_active_map().get_name() )

                            # Track the next level's name in session; we'll need it when
                            # we handle the forwarded "finalize transition" event.
                            self.set_session_variable("net.transition.target", next_map_name)


                            # Send transition command to all clients
                            network_controller.send_level_complete_with_next_map_name(next_map_name, control_center, universe = self)

                        # If not complete, then we should check to see if all players are dead...
                        else:

                            # Assume all dead
                            failed = True

                            # Fetch active map
                            m = self.get_active_map()


                            # Prepare loop
                            i = 0
                            max_players = int( self.get_session_variable("net.player-limit").get_value() )

                            # Loop all potential players in this coop universe
                            while ( (failed) and (i < max_players) ):

                                # 1-based within maps
                                player_id = (1 + i)


                                # Find the entity by that player id
                                player = m.get_entity_by_name("player%d" % player_id)

                                # Validate
                                if (player):

                                    # If the player is active, then the level is not failed
                                    if ( player.get_status() == STATUS_ACTIVE ):

                                        # Still a chance to win!
                                        failed = False


                                # Loop
                                i += 1


                            # Is it game over, man?
                            if (failed):

                                # First, flag the game as no longer in progress
                                self.set_session_variable("net.game-in-progress", "0")


                                # Add a "level failed" newsfeeder item
                                control_center.get_window_controller().get_newsfeeder().post({
                                    "type": NEWS_NET_LEVEL_FAILED,
                                    "title": control_center.get_localization_controller().get_label("level-failed:title"),
                                    "content": control_center.get_localization_controller().get_label("level-failed:message")
                                })


                                # Fetch the window controller
                                window_controller = control_center.get_window_controller()

                                # Hook into the window controller to receive a forwarded event
                                window_controller.hook(self)


                                # Set a brief delay on the window controller
                                window_controller.delay(NET_TRANSITION_DELAY)

                                # Call for an app-level fade once that delay completes
                                window_controller.fade_out(
                                    on_complete = "fwd.net.transition.finalize"
                                )


                                # Just "transition" to the same map
                                next_map_name = self.get_active_map().name

                                # Track the next level's name in session; we'll need it when
                                # we handle the forwarded "finalize transition" event.
                                self.set_session_variable("net.transition.target", next_map_name)


                                # Send transition command to all clients
                                network_controller.send_level_failed_with_next_map_name(next_map_name, control_center, universe = self)



            """ Debug """
            # While recording GIF animation replay files, I want the debug key to unpause the universe.
            if ( INPUT_DEBUG in control_center.get_input_controller().get_gameplay_input() ):

                # universe defaults to paused when in recording mode, just to give me time to prepare...
                self.unpause()
            """ End Debug """



            # Process the active map (unless the map / universe is "busy")
            #if ( ( self.get_game_state() == GAME_STATE_ACTIVE ) and ( not m.is_busy() ) and ( not self.is_busy() ) ):
            if ( ( not self.is_paused() ) and ( not m.is_busy() ) and ( not self.is_busy() ) ):

                """
                m.process(gameplay_input, self.widget_dispatcher, self.network_controller, self, self.session, self.quests)
                m.process_drama(self, self.session)
                """

                m.process(control_center, self)

                m.process_drama(control_center, self)


                # Do we need to play any sound effect?
                #sfx_keys = m.process_sound()
                #for sfx_key in sfx_keys:
                #    self.sound_effects[sfx_key].play()


                m.post_process(control_center, universe = self)


                # Has the map requested a screen shake?
                """
                if (m.requested_shake_tuple):

                    (intensity, style) = m.requested_shake_tuple

                    self.shake_screen(intensity, style)

                    # the map's request has been heard...
                    m.requested_shake_tuple = None
                """


                # Server checks to see if any enemy is requesting an ai
                # update.  If so, server syncs all enemy ai to all clients.
                if ( control_center.get_network_controller().get_status() == NET_STATUS_SERVER ):

                    # Assume
                    enemies_require_ai_sync = False

                    # Loop map enemies
                    for e in m.get_entities_by_type(GENUS_ENEMY):

                        # Does the enemy require an ai update?
                        if (e.requires_ai_update):

                            # Update assumption
                            enemies_require_ai_sync = True

                        # Always disable flag
                        e.requires_ai_update = False

                    # Do we need to sync ai?
                    if (enemies_require_ai_sync):

                        # Sync enemy AI to all clients.
                        # The enemy AI data will include current target name.
                        control_center.get_network_controller().send_sync_enemy_ai(control_center, universe = self)


                # Process any equipped Item object
                for item in self.equipped_inventory:

                    # Really, we just want to know if the item has expired a duration timer,
                    # which would require us to reset cached item attribute results...
                    if ( item.process() == ITEM_PROCESS_RESULT_EXPIRED ):

                        # Clear cached calculations
                        self.clear_item_attribute_result_cache()


                # Having processed everything, the player may have picked up some gold.  Let's update the universe's current
                # tally of the "remaining gold" for the current map...
                self.set_map_gold_remaining( self.active_map_name, m.remaining_gold_count() )


                # Count another frame for the overall time played counter
                self.get_session_variable("core.time.played").increment_value(1)


            else:

                m.process_cutscene(control_center, self)


            #if ( (self.get_game_state() == GAME_STATE_ACTIVE) ):
            #    self.process_screen_shake()



            # Check to see if the player object has entered a new map.  If so, set the
            # new map as the active map, then add a new player object at the appropriate position.
            #for player in m.master_plane.entities[GENUS_PLAYER]:
            player = self.get_local_player()

            # Validate
            if (player):

                rPlayer = player.get_rect()
                rMap = m.get_relative_rect()

                # Out-of-bounds?
                if ( not intersect(rPlayer, rMap) ):

                    # If the map is redlined and the player fell down the bottom, then we must destroy the player...
                    #if ( m.is_redlined() and (rPlayer[1] > rMap[3]) ):
                    if (False):

                        # (Disabled currently)
                        player.queue_death_by_cause(DEATH_BY_OUT_OF_BOUNDS)

                    else:

                        #print "Out of bounds, looking for a new map..."


                        # First, let's check to see if the player hit a fall region.
                        for r in m.get_fall_regions():

                            # Translate from tile coordinates to absolute coordinates
                            rFallRegion = (
                                r[0] * TILE_WIDTH,
                                m.get_height_in_pixels(),
                                r[1] * TILE_WIDTH,
                                TILE_HEIGHT
                            )

                            # Check intersection
                            if ( intersect(rPlayer, rFallRegion) ):

                                # Player dies by fall
                                player.queue_death_by_cause(DEATH_BY_OUT_OF_BOUNDS)


                        # Check perimeter maps for a new area...
                        for key in self.visible_maps[LAYER_FOREGROUND]:

                            if ( intersect( rPlayer, self.visible_maps[LAYER_FOREGROUND][key].get_relative_rect( (m.x, m.y) ) ) ):

                                log2( "Found map:  %s\n" % key, "player rect:", rPlayer )

                                # We found a new map.  Before doing anything else, let's save the memory of the map we are leaving...
                                m.save_memory(self)


                                # Let's set this new map we've landed on as the active map, updating variable "m" as the newly-activated map...
                                m_new = self.activate_map_on_layer_by_name(key, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center)


                                # Calculate relative distance between the old map and the new map
                                (relX, relY) = (
                                    (m_new.x * TILE_WIDTH) - (m.x * TILE_WIDTH),
                                    (m_new.y * TILE_HEIGHT) - (m.y * TILE_HEIGHT)
                                )

                                # We'll position the player on the new map accordingly
                                (spawnX, spawnY) = (
                                    player.get_x() - relX,
                                    player.get_y() - relY
                                )


                                # Add a new player entity to the new map and set its position...
                                new_player = m_new.create_player().describe({
                                    "name": player.name,
                                    "genus": GENUS_PLAYER,
                                    "absolute-x": spawnX,
                                    "absolute-y": spawnY
                                })

                                # Remember the player's new position as they enter the new map...
                                self.set_session_variable("core.player1.x", "%d" % spawnX)
                                self.set_session_variable("core.player1.y", "%d" % spawnY)


                                # Colorify the new player
                                new_player.colorify(
                                    self.get_session_variable("core.player1.colors").get_value()
                                )


                                # New player object shall face in the same direction
                                new_player.direction = player.direction

                                # Also, new player object shall have the same "last attempted" data
                                new_player.ai_state.last_lateral_move = player.ai_state.last_lateral_move
                                new_player.ai_state.last_attempted_lateral_move = player.ai_state.last_attempted_lateral_move

                                new_player.ai_state.last_vertical_move = player.ai_state.last_vertical_move
                                new_player.ai_state.last_attempted_vertical_move = player.ai_state.last_attempted_vertical_move


                                # Just in case, remove any entity by the given name on the new map...
                                m_new.remove_entity_by_type_and_name(GENUS_PLAYER, player.name)

                                # Also remove the old player from the old map
                                m.remove_entity_by_type_and_name(GENUS_PLAYER, player.name)


                                # Now, add the player to the new map...
                                m_new.master_plane.entities[GENUS_PLAYER].append(new_player)


                                # Instruct the newly activated map to handle any logic relating to a player entering...
                                #m_new.handle_player_arrival(control_center, universe = self)


                                # Flag that we should discard non-adjacent maps upon the camera reaching its target...
                                self.discard_offscreen_maps_on_camera_shift_completion = True


                                # Raise an autosave event as we arrive on the new map
                                results.add(
                                    action = "autosave"
                                )


                                # Let's clear any cached window regions at this map transition point...
                                control_center.get_window_controller().clear_cache()


                                # We found a map to visit, so let's exit this loop
                                break


            # Fetch the active map
            m = self.get_active_map()

            # Validate
            if (m):

                # Get the wave tracker
                wave_tracker = m.get_wave_tracker()

                # Check to see if we have failed the current wave.
                if ( wave_tracker.is_wave_failed() ):

                    # See if we have a valid on-fail script
                    if ( m.does_script_exist( wave_tracker.get_wave_param("on-fail") ) ):

                        log2( "Running on-fail script" )

                        # Run that script now
                        m.run_script(
                            wave_tracker.get_wave_param("on-fail"),
                            control_center,
                            universe = self
                        )

                        # We only want to run the failure script once.  Thus, we're going to erase
                        # the on-fail script now.
                        wave_tracker.set_wave_param("on-fail", "")

                        # AT this point, I'm also going to clear out the on-complete script as well.
                        # Nothing good can happen, really, from keeping it there.  (Post-death "completions," etc., we don't want.)
                        wave_tracker.set_wave_param("on-complete", "")

                # Check to see if we completed the current wave
                elif ( wave_tracker.is_wave_complete() ):

                    log2( "WAVE COMPLETE!" )

                    # See if we have a valid on-complete script
                    if ( m.does_script_exist( wave_tracker.get_wave_param("on-complete") ) ):

                        log2( "Running on-complete script" )

                        # Run that script now
                        m.run_script(
                            wave_tracker.get_wave_param("on-complete"),
                            control_center,
                            universe = self
                        )

                        # We only want to run the script once.  Thus, we're going to erase the on-complete script now.
                        wave_tracker.set_wave_param("on-complete", "")

                        # (?) I think for now I'm going to leave the on-fail script in place, in case I want to allow
                        # "you beat the final boss but then fell in the lava before you reached the princess" scenarios.
                        #pass


        # If the network controller has a global lock, we'll still process any cutscene / script events.
        # We'll also do limited network processing. (?)
        else:

            # Stupid GIFs don't network!
            if ( self.get_session_variable("core.is-gif").get_value() == "0" ):

                # Fetch the network controller
                network_controller = control_center.get_network_controller()

                # Check netplay messages here???
                network_controller.process(control_center, universe = self)

                command = network_controller.get_next_command()

                while (command):

                    log( "Received command:  ", command )
                    self.process_network_command(command, control_center)

                    command = network_controller.get_next_command()


            # Fetch active map
            m = self.get_active_map()

            # Process cutscene / scripted events
            m.process_cutscene(control_center, universe = self)


        # Handle each event we received
        event = results.fetch()

        # All of them!
        while (event):

            # Handle the event
            self.handle_event(event, control_center, universe = self)

            # Forward event to any listener
            self.forward_event_to_listeners(event, control_center, universe = self)


            # Loop
            event = results.fetch()


    # Handle an event
    def handle_event(self, event, control_center, universe):

        # Convenience
        (action, params) = (
            event.get_action(),
            event.get_params()
        )


        # Show debug message
        if (action == "universe:debug"):

            self.handle_universe_debug_event(event, control_center, universe)

        # Autosave
        elif (action == "autosave"):

            self.handle_autosave_event(event, control_center, universe)

        elif ( (False) and (action == "debug:save-state") ):

            log( "Considering autosave100 debug save..." )
            if ( control_center.get_network_controller().get_status() == NET_STATUS_OFFLINE ):

                log( "\t...committing save." )

                # Fetch save controller
                save_controller = control_center.get_save_controller()


                # Lastly, let's commit an autosave to commemorate the player's arrival on a new screen...
                xml = save_controller.construct_metadata_with_title("Autosave", universe = self)


                # Generate filesave preview image
                self.generate_filesave_thumbnail()

                player = universe.get_local_player()

                (spawnX, spawnY) = (
                    player.get_x(),
                    player.get_y()
                )

                # Remember the player's new position as they enter the new map...
                self.set_session_variable("core.player1.x", "%d" % spawnX)
                self.set_session_variable("core.player1.y", "%d" % spawnY)

                # Commit the save...
                save_controller.save_to_slot(slot = 100, universe = self, autosave = True, metadata = xml)



                path = os.path.join( self.get_working_save_data_path(), "autosave100", "history")

                # Make sure the path exists
                ensure_path_exists(path)

                # Compile a memory string
                xml = self.get_active_map().save_state().compile_inner_xml_string()#compile_memory_string()

                # Save to file
                f = open( os.path.join(path, "%s.history.xml" % self.get_active_map().name), "w" )
                f.write(xml)
                f.close()



                log2( "debug:  autosave100 complete" )

        # Run a script
        elif ( action.startswith("script:") ):

            self.get_active_map().run_script(
                action.split(":", 1)[-1],
                control_center,
                universe
            )

        elif (action == "universe:kill-player"):
            self.get_active_map().get_entity_by_name("player1").queue_death_by_cause(DEATH_BY_VAPORIZATION)

            log2( "Universe killed the player." )

        elif (action == "network:ping"):

            self.handle_network_ping_event(event, control_center, universe)

        elif (action == "server:sync-ai"):

            self.handle_server_sync_ai_event(event, control_center, universe)

        elif (action == "network:sync-local-player"):

            self.handle_network_sync_local_player_event(event, control_center, universe)

        elif (action == "server:ping-web-server"):

            self.handle_server_ping_web_server_event(event, control_center, universe)

        # Finalize a forwarded netplay level transition
        elif (action == "fwd.net.transition.finalize"):

            self.handle_fwd_net_transition_finalize_event(event, control_center, universe)


    # A generic debug event for testing during development
    def handle_universe_debug_event(self, event, control_center, universe):

        # Events that result from handling the event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Simple print
        log2( "Debug message received at %s:\n" % time.time(), params["message"] )


        # Return events
        return results


    # Transition to a given map
    def handle_fwd_net_transition_finalize_event(self, event, control_center, universe):

        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the menu controller;
        menu_controller = control_center.get_menu_controller()


        # Unhook universe from the window controller
        window_controller.unhook(self)


        # Clear all visible maps
        self.visible_maps[LAYER_FOREGROUND].clear()


        # Which map do we need to load?
        next_map_name = self.get_session_variable("net.transition.target").get_value()

        # Transition the local map
        universe.activate_map_on_layer_by_name(next_map_name, LAYER_FOREGROUND, control_center = control_center, ignore_adjacent_maps = True)

        # Immediately center the camera on the active map (?)
        universe.center_camera_on_map( universe.get_active_map() )


        # Server will update the web server with the new map name.
        if ( control_center.get_network_controller().get_status() == NET_STATUS_SERVER ):

            # Update
            control_center.get_network_controller().web_update_current_level(control_center, universe)

        # Reset various lobby metrics (vote to skip counter, player status, etc.)
        universe.prepare_multiplayer_lobby()


        # Clear all existing menus
        menu_controller.clear()

        # Add a multiplayer lobby menu
        menu_controller.add(
            widget_dispatcher.create_net_lobby()
        )


        # Force the game to 1st pause state
        universe.unpause(force = True).pause()


        # Invalidate the splash controller
        control_center.get_splash_controller().invalidate()

        # App-level fade in
        window_controller.fade_in()


    # During netplay, we can send out ping requests to other players.
    def handle_network_ping_event(self, event, control_center, universe):

        # Events that result from handling the event
        results = EventQueue()

        # Simply sync the AI via the network controller
        control_center.get_network_controller().send_ping(control_center, universe)

        # Return events
        return results


    # During netplay, the server will periodically sync all enemies' AI data to each client
    def handle_server_sync_ai_event(self, event, control_center, universe):

        # Events that result from handling the event
        results = EventQueue()

        # Simply sync the AI via the network controller
        control_center.get_network_controller().send_sync_enemy_ai(control_center, universe)
        #event = lambda s = self, c = control_center, u = universe: s.send_sync_enemy_ai(c, u)

        # Return events
        return results


    # During netplay, players will periodically update their location to all other players.
    def handle_network_sync_local_player_event(self, event, control_center, universe):

        # Resultant events
        results = EventQueue()

        # Get local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )

        # Send sync message
        control_center.get_network_controller().send_sync_player_by_id(player_id, control_center, universe)

        # Return events
        return results


    # During netplay, the server should intermittently ping the web server
    # to keep the session active (in the lobby browser).
    def handle_server_ping_web_server_event(self, event, control_center, universe):

        # Events that result from handling the event
        results = EventQueue()

        # Simply update the player count; this will refresh the web server's timestamp record
        control_center.get_network_controller().web_update_player_count(control_center, universe)

        # Return events
        return results


    # Commit an autosave
    def handle_autosave_event(self, event, control_center, universe):

        # Forward
        self.commit_autosave(control_center, universe)


    # Okay, this is the actual commit function
    def commit_autosave(self, control_center, universe):

        # Fetch save controller
        save_controller = control_center.get_save_controller()


        # Create generic XML metadata
        xml = save_controller.construct_metadata_with_title("Autosave", universe = self)

        # Save the current display to a temporary file.  We'll use this
        # temporary file as the source of the thumbnail for the autosave.
        self.generate_filesave_thumbnail()

        # Commit the save...
        save_controller.save_to_slot(slot = 1, universe = universe, autosave = True, metadata = xml)


    # Ignore camera, provide offset explicitly
    def draw_map_on_layer_with_explicit_offset(self, map_name, layer, sx, sy, tilesheet_sprite, additional_sprites, game_mode, control_center, max_x = SCREEN_WIDTH, max_y = SCREEN_HEIGHT, scale = None, gl_color = (1, 1, 1, 1)):

        #log2( "sx, sy = ", (sx, sy) )

        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the splash controller;
        splash_controller = control_center.get_splash_controller()


        # Also, fetch a handle to the default text renderer
        text_renderer = window_controller.get_default_text_controller().get_text_renderer()


        #layer = LAYER_BACKGROUND
        # Is this map on the roster of visible (or unsaved) maps?
        if (not (map_name in self.visible_maps[layer])):

            # Load a copy in...
            self.visible_maps[layer][map_name] = self.create_map(
                name = map_name,
                x = self.map_data[layer][ map_name ].x,
                y = self.map_data[layer][ map_name ].y,
                options = {
                    "is-new": False
                },
                control_center = control_center
            )

            self.visible_maps[layer][map_name].load(
                filepaths = {
                    "map": os.path.join( self.get_working_map_data_path(None), "%s.xml" % map_name ),
                    "dialogue": os.path.join( self.get_working_map_data_path(None), "dialogue", "%s.dialogue.xml" % map_name ),
                    "menu": os.path.join( self.get_working_map_data_path(None), "levelmenus", "%s.levelmenus.xml" % map_name )
                },
                options = {
                    "is-new": False
                },
                control_center = control_center
            )


        #rCameraScaled = ( int(self.camera.x / BACKGROUND_MAP_PARALLAX_SCALE), int(self.camera.y / BACKGROUND_MAP_PARALLAX_SCALE), SCREEN_WIDTH, SCREEN_HEIGHT )

        # Grab handle to the map object
        m = self.visible_maps[layer][map_name]

        #if ( layer == LAYER_FOREGROUND and m != self.get_active_map() ):
        #    return

        #sx *= -1
        #sy *= -1

        #log2( "rendering to pad.common @", (rx, ry) )

        if (scale == None):
            scale = SCALE_BY_LAYER[layer]

        #print (sx, sy)
        m.draw( int(sx), int(sy), tilesheet_sprite, additional_sprites, game_mode, gl_color = gl_color, text_renderer = text_renderer, control_center = control_center, max_x = max_x, max_y = max_y, scale = scale )


    # Prerender the parallax layer (centered* on the current camera position)
    # to the parallax scratch pad.  (*prerender will not center if it means
    # including parallax data irrelevant to current level.)
    def prerender_parallax_layer(self, tilesheet_sprite, additional_sprites, game_mode, control_center):

        # Fetch the window controller
        window_controller = control_center.get_window_controller()


        # Fetch the scratch pads we'll be using
        (common_scratch_pad, parallax_scratch_pad) = (
            window_controller.get_scratch_pad("common"),
            window_controller.get_scratch_pad("parallax")
        )


        # Render to the common scratch pad first
        window_controller.render_to_scratch_pad("parallax")

        # Clear the common scratch pad
        window_controller.get_geometry_controller().draw_rect(0, 0, common_scratch_pad.get_width(), common_scratch_pad.get_height(), (20, 20, 20))


        # Fetch scale data for parallax layer
        scale = SCALE_BY_LAYER[LAYER_BACKGROUND]
        parallax = PARALLAX_BY_LAYER[LAYER_BACKGROUND]


        # Stash the current camera location
        (cameraX, cameraY) = (
            self.camera.x,
            self.camera.y
        )

        # Define the region we'll check each parallax map's adjusted location against.
        # Note that we use the scratch pad's dimensions here, instead of the typical screen dimensions.
        rPerimeter = ( cameraX, cameraY, common_scratch_pad.get_width(), common_scratch_pad.get_height() )

        # Figure the range the camera can travel while on this map
        rCameraBounds = self.get_camera_region_for_map_on_layer( self.get_active_map().name, LAYER_FOREGROUND )


        # I want the sample we take from the parallax layer (that we prerender) to
        # center on the current camera location (i.e. room to spare on the left and the right)
        rCentered = offset_rect(
            rPerimeter,
            x = -1 * int( ( common_scratch_pad.get_width() - self.camera.get_width() ) / 2 ),
            y = -1 * int( ( common_scratch_pad.get_height() - self.camera.get_height() ) / 2 )
        )


        # How far can the camera move (assume start from flush left / top) before we run out of prerender data?
        widthPossible = int( (1024 - 640) / 0.85 )
        heightPossible = int( (1024 - 480) / 0.85 )

        # Adjust the camera render region by the extra room available
        (bonus_x, bonus_y) = (
            int(widthPossible / 4),
            int(heightPossible / 4)
        )

        """
        # Apply bonus to assumed centered region
        rPrerenderRegion = offset_rect(
            rCentered,
            x = -int(bonus_x / 2),
            y = -int(bonus_y / 2),
            w = 2 * int(bonus_x / 2), # Trying to account for rounding, keep the bonus on each side completely equal
            h = 2 * int(bonus_y / 2)
        )
        """

        # Define the region wtihin which the camera can exist without requiring a prerender refresh
        rPrerenderRegion = (rCentered[0] - bonus_x, rCentered[1] - bonus_y, 640 + widthPossible, 480 + heightPossible)


        if (1):
            # The sampled region must fit entirely within the available camera bounds for the current level.
            # If it does not, we must adjust both the "centered" region and the "prerender" region.
            if ( rCentered[0] < rCameraBounds[0] ):

                # It must fit entirely
                rCentered = offset_rect(
                    rCentered,
                    x = (rCameraBounds[0] - rCentered[0])
                )

                # Adjust prerender region to start at that left edge and span the entire bonus region
                rPrerenderRegion = ( rCentered[0], rPrerenderRegion[1], rPrerenderRegion[2], rPrerenderRegion[3] )

            # Off the right edge?
            elif ( (rCentered[0] + rCentered[2]) > (rCameraBounds[0] + rCameraBounds[2]) ):

                # Fit
                rCentered = offset_rect(
                    rCentered,
                    x = -( (rCentered[0] + rCentered[2]) - (rCameraBounds[0] + rCameraBounds[2]) )
                )

                # Adjust prerender region to fit against right edge of current level
                rPrerenderRegion = ( rCentered[0] + rCentered[2] - rPrerenderRegion[2], rPrerenderRegion[1], rPrerenderRegion[2], rPrerenderRegion[3] )


            # Y-axis
            if ( rCentered[1] < rCameraBounds[1] ):

                # It must fit entirely
                rCentered = offset_rect(
                    rCentered,
                    y = (rCameraBounds[1] - rCentered[1])
                )

                # Adjust prerender region to start at that top edge and span the entire bonus region
                rPrerenderRegion = ( rPrerenderRegion[0], rCentered[1], rPrerenderRegion[2], rPrerenderRegion[3] )

            # Off the bottom edge?
            elif ( (rCentered[1] + rCentered[3]) > (rCameraBounds[1] + rCameraBounds[3]) ):

                # Fit
                rCentered = offset_rect(
                    rCentered,
                    y = -( (rCentered[1] + rCentered[3]) - (rCameraBounds[1] + rCameraBounds[3]) )
                )

                # Adjust prerender region to fit against right edge of current level
                rPrerenderRegion = ( rPrerenderRegion[0], rCentered[1] + rCentered[3] - rPrerenderRegion[3], rPrerenderRegion[2], rPrerenderRegion[3] )


        # Configure the camera with the arduously-calculated prerender region
        self.camera.configure({
            "dirty": False,                          # Right now we're taking care of prerender stuff
            "prerender-bounds": rPrerenderRegion,    # If the camera leaves the region we've sampled, then we'll have to update prerendered parallax data
            "prerender-location": (cameraX, cameraY) # Location of the camera when we calculate the prerender
        })

        # Also remember how much of an offset we applied to the prerender layer while centering it (as much as we could)...
        self.prerender_offsets = (
            rCentered[0] - rPerimeter[0],
            rCentered[1] - rPerimeter[1]
        )


        # Calculate the parallax offset (to scale) at the top-left corner of the region we'll center from.
        (px, py) = self.camera.get_parallax_offsets_at_location(rPrerenderRegion[0], rPrerenderRegion[1], parallax = parallax)

        if (0):
            log2(
                "rPerimeter:", rPerimeter, "\n",
                "rCentered:", rCentered, "\n",
                "rCameraBounds:", rCameraBounds, "\n",
                "rPrerenderRegion:", rPrerenderRegion, "\n",
                "\tbonus:", (bonus_x, bonus_y), "\n",
                "\twidthPossible:", widthPossible, "\n",
                "offsets:", self.prerender_offsets, "\n",
                "px, py:", (px, py)
            )


        znames = []
        # Now loop each visible map
        for name in self.map_data[LAYER_BACKGROUND]:#visible_maps[layer]:

            # Get the base region for this map at the given scale
            rMap = self.get_base_region_for_map_on_layer(name, LAYER_BACKGROUND, scale = scale)

            # Adjust for the parallax offset at the present camera location
            rAdjusted = offset_rect(
                rMap,
                x = px,
                y = py
            )


            # If the parallax-adjusted rectangle appears within the present camera location at all,
            # then we shall render the map.
            if ( intersect(rCameraBounds, rAdjusted) ):

                znames.append( "%s (%d, %d, %d, %d)" % (name, rAdjusted[0], rAdjusted[1], rAdjusted[2], rAdjusted[3]) )

                # Renderer parallax layer at a dim level, low brightness
                # old: 0.5 rgb, 1.0 alpha
                self.draw_map_on_layer_with_explicit_offset(name, LAYER_BACKGROUND, rAdjusted[0] - rPrerenderRegion[0] + 0*192, rAdjusted[1] - rPrerenderRegion[1] + 0*272, tilesheet_sprite, additional_sprites, MODE_GAME, control_center, max_x = 1024, max_y = 1024, scale = scale, gl_color = (0.5, 0.25, 0.0, 1.0))


        ##window_controller.get_geometry_controller().draw_rect_frame(192, 272, 640, 480, (225, 25, 25, 0.75), 2)


        # Horizontal blur pass to common scratch pad
        window_controller.render_to_scratch_pad("common")

        # Activate and configure directional blur shader
        window_controller.activate_shader("directional-blur")
        window_controller.configure_directional_blur(0, 1024.0)

        # Render to common with blur
        window_controller.get_gfx_controller().draw_texture( parallax_scratch_pad.get_texture_id(), 0, 0, parallax_scratch_pad.get_width(), parallax_scratch_pad.get_height() )


        # Render back to parallax scratch pad with the second directional blur pass (vertical)
        window_controller.render_to_scratch_pad("parallax")

        # Configure already-active directional blur shader
        window_controller.configure_directional_blur(1, 1024.0)

        # Render with blur from the common pad (which holds the 1st pass)
        window_controller.get_gfx_controller().draw_texture( common_scratch_pad.get_texture_id(), 0, 0, common_scratch_pad.get_width(), common_scratch_pad.get_height() )

        # Deactivate shader
        window_controller.deactivate_shader()


        # Carry on rendering to primary framebuffer; we've completed the prerender, finally...
        window_controller.render_to_primary()



        z = "Prerender complete!\n"
        for n in znames:
            z += "\t%s\n" % n
        log2( z )


    """
    def draw_parallax(self, tilesheet_sprite, additional_sprites, game_mode, control_center):

        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the splash controller;
        splash_controller = control_center.get_splash_controller()


        # Also, fetch a handle to the default text renderer
        text_renderer = window_controller.get_default_text_controller().get_text_renderer()


        layer = LAYER_BACKGROUND
        for map_name in self.map_data[layer]:

            # Is this map on the roster of visible (or unsaved) maps?
            if (not (map_name in self.visible_maps[layer])):

                # Load a copy in...
                self.visible_maps[layer][map_name] = self.create_map(
                    name = map_name,
                    x = self.map_data[layer][ map_name ].x,
                    y = self.map_data[layer][ map_name ].y,
                    options = {
                        "is-new": False
                    },
                    control_center = control_center,
                    universe = self
                )

                self.visible_maps[layer][map_name].load(
                    filepaths = {
                        "map": os.path.join( self.get_working_map_data_path(None), "%s.xml" % map_name ),
                        "dialogue": os.path.join( self.get_working_map_data_path(None), "dialogue", "%s.dialogue.xml" % map_name ),
                        "menu": os.path.join( self.get_working_map_data_path(None), "levelmenus", "%s.levelmenus.xml" % map_name )
                    },
                    options = {
                        "is-new": False
                    },
                    control_center = control_center
                )


        rCameraScaled = ( int(self.camera.x / BACKGROUND_MAP_PARALLAX_SCALE), int(self.camera.y / BACKGROUND_MAP_PARALLAX_SCALE), SCREEN_WIDTH, SCREEN_HEIGHT )
        sx = 0

        for map_name in self.visible_maps[LAYER_BACKGROUND]:

            # Grab handle to the map object
            m = self.visible_maps[LAYER_BACKGROUND][map_name]


            # Only render if it's visible...
            r2 = (m.x * TILE_WIDTH, m.y * TILE_HEIGHT, m.get_width() * TILE_WIDTH, m.get_height() * TILE_HEIGHT)


            # Visible?
            if (True or intersect(rCameraScaled, r2)):

                # Typically, we only render the maps in the universe while the universe is active (i.e. not paused, etc.)
                # However, we also will render fresh visual data if the splash controller is "dirty" and thus in need of fresh data.
                renderable = ( ( splash_controller.is_dirty() ) or (self.get_game_state() == GAME_STATE_ACTIVE) )

                m.draw(-rCameraScaled[0] + sx, -rCameraScaled[1] + 0, tilesheet_sprite, additional_sprites, game_mode, gl_color = (1, 1, 1), text_renderer = text_renderer, window_controller = window_controller, scale = BACKGROUND_MAP_SCALE)
    """


    def draw_game(self, tilesheet_sprite, additional_sprites, game_mode, control_center):

        # Quickly check for custom tilesheet.  Overwrite param if we have one!
        if (self.custom_tilesheet):

            # We'll use the custom tilesheet for rendering this universe
            tilesheet_sprite = self.custom_tilesheet


        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the splash controller;
        splash_controller = control_center.get_splash_controller()


        # Also, fetch a handle to the default text renderer
        text_renderer = window_controller.get_default_text_controller().get_text_renderer()



        # If we're "ready" to prerender the visible parallax layer, then we'll do so now.
        if (self.prerender_status == PRERENDER_STATUS_READY):

            # Prerender the parallax layer
            self.prerender_parallax_layer(tilesheet_sprite, additional_sprites, game_mode, control_center)

            # We're done prerendering
            self.prerender_status = PRERENDER_STATUS_DONE



        # Grab the active map's name
        active_map_name = self.get_active_map().name


        # Stash current camera position
        (cameraX, cameraY) = (
            self.camera.x,
            self.camera.y
        )

        # Define screen camera position
        #rCamera = ( int(self.camera.x), int(self.camera.y), SCREEN_WIDTH, SCREEN_HEIGHT)
        # Define render offset (to account for simple hslide controller, really)
        #sx = 0*self.hslide_controller.get_interval()


        # At first, I'm going to assume that we'll just be rendering the foreground layer in real-time.
        # We'll have to also render the background (parallax) layer, though, if the prerender isn't done.
        layers = (LAYER_FOREGROUND,)


        # First, let's render the prerendered parallax layer, if it's done...
        if ( (not pygame.key.get_pressed()[K_LSHIFT]) and self.prerender_status == PRERENDER_STATUS_DONE):

            # Parallax offsets at the current camera location
            (px, py) = self.camera.get_parallax_offsets_at_location(cameraX, cameraY, parallax = PARALLAX_BY_LAYER[LAYER_BACKGROUND])

            # Parallax offsets at the left-most prerender cache (camera flush against left boundary)
            (pxCached, pyCached) = self.camera.get_parallax_offsets_at_location(self.camera.prerender_bounds[0], self.camera.prerender_bounds[1], parallax = PARALLAX_BY_LAYER[LAYER_BACKGROUND])


            # Relative deltas between the camera's positions and boundaries
            (cdx, cdy) = (
                cameraX - self.camera.prerender_bounds[0], # always >= 0
                cameraY - self.camera.prerender_bounds[1]  # always >= 0
            )


            # Render position for the prerendered parallax layer
            (rx, ry) = (
                -pxCached - cdx + px, # Offset by the built-in parallax; offset by relative camera delta; add in full-distance parallax offset
                -pyCached - cdy + py  #     (This honestly took me several hours to add up, it was pretty frustrating!)
            )


            # Get a reference to the parallax scratch pad
            parallax_scratch_pad = window_controller.get_scratch_pad("parallax")

            # Render (prerendered) parallax layer
            # old: 0.1 alpha
            window_controller.get_gfx_controller().draw_texture( parallax_scratch_pad.get_texture_id(), int(rx), int(ry), parallax_scratch_pad.get_width(), parallax_scratch_pad.get_height(), (1, 1, 1, 0.25) )#drawbuffer2(-shx, shy)

            #log2( "Rendered parallax prerender" )

        # If the prerender isn't done, then we'll have to render both layers in real-time.
        else:

            # Update layer targets, rendering background first of course...
            layers = (LAYER_BACKGROUND, LAYER_FOREGROUND)

            #log2( "Rendering background in realtime" )


        # Render layer targets (typically just the foreground here)
        for layer in layers:

            # Foreground is always 1x scale
            scale = SCALE_BY_LAYER[layer]
            parallax = PARALLAX_BY_LAYER[layer]


            # Define the visible camera region (just set to the current camera location)
            rPerimeter = (cameraX, cameraY, SCREEN_WIDTH, SCREEN_HEIGHT)

            # Calculate the parallax offset (to scale) at the current camera position
            # (i.e. there is no parallax while exclusively  "zoomed" on the background,
            # but there is when showing both layers.
            (px, py) = self.camera.get_parallax_offsets_at_location( rPerimeter[0], rPerimeter[1], parallax = parallax )


            # Now loop each visible map
            for name in self.visible_maps[layer]:

                # Get the base region for this map at the given scale
                rMap = self.get_base_region_for_map_on_layer(name, layer, scale = scale)

                # Adjust for the parallax offset at the present camera location
                rAdjusted = offset_rect(
                    rMap,
                    x = px,
                    y = py
                )


                # If the parallax-adjusted rectangle appears within the present camera location at all,
                # then we shall render the map.
                if ( intersect(rPerimeter, rAdjusted) ):

                    # If this map is the active map, then we'll render it at full color, full opacity, irregardless!
                    if ( name == self.active_map_name ):

                        if ( True or not pygame.key.get_pressed()[K_LSHIFT] ):
                            # This is the map we're on, show it bright!
                            self.draw_map_on_layer_with_explicit_offset(name, layer, rAdjusted[0] - rPerimeter[0], rAdjusted[1] - rPerimeter[1], tilesheet_sprite, additional_sprites, MODE_GAME, control_center, scale = scale, gl_color = (1, 1, 1, 1))


                    # An inactive map on the foreground layer renders dimmed...
                    else:

                        # Foreground only, just dim
                        if (layer == LAYER_FOREGROUND):

                            if ( not pygame.key.get_pressed()[K_LSHIFT] ):
                                self.draw_map_on_layer_with_explicit_offset(name, layer, rAdjusted[0] - rPerimeter[0], rAdjusted[1] - rPerimeter[1], tilesheet_sprite, additional_sprites, MODE_GAME, control_center, scale = scale, gl_color = (0.5, 0.5, 0.5, .5))

                        # Render background maps very dimmed
                        elif (layer == LAYER_BACKGROUND):

                            if ( not pygame.key.get_pressed()[K_LSHIFT] ):
                                self.draw_map_on_layer_with_explicit_offset(name, layer, rAdjusted[0] - rPerimeter[0], rAdjusted[1] - rPerimeter[1], tilesheet_sprite, additional_sprites, MODE_GAME, control_center, scale = scale, gl_color = (1, 1, 1, 0.05))


        # Fetch the active map
        m = self.get_active_map()

        # Validate
        if (m):

            # Grab the wave tracker
            wave_tracker = m.get_wave_tracker()


            # See if we can find a timer that matches the current wave's "active timer."  I expect to use
            # these only in challenge rooms.
            timer = self.get_timer_controller().get_timer_by_name(
                wave_tracker.get_wave_param("active-timer")
            )

            # Did we find a timer by that name?
            if (timer):

                # Get the time remaining with 2 decimal places
                seconds = timer.get_time_remaining_in_seconds(precision = 1)

                # Default color
                color = (225, 225, 225)


                # If less than 10 seconds remain, keep both decimal places
                if (seconds < 10):

                    # Danger color
                    color = (225, 25, 25)

                # If we're between 10 and 30 seconds, keep just one decimal place
                elif (seconds < 30):

                    # Warning color
                    color = (192, 160, 40)

                # Otherwise, drop the decimal entirely
                else:

                    # No decimal
                    seconds = round(seconds)

                    # Default color
                    color = (225, 225, 225)


                # Render the timer with the given wave timer label...
                text_renderer.render_with_wrap( "%s" % wave_tracker.get_wave_param("active-timer-label"), int(SCREEN_WIDTH / 2), 15, (145, 145, 145), align = "center" )
                text_renderer.render_with_wrap( "%ss" % seconds, int(SCREEN_WIDTH / 2), 35, color, align = "center" )


        # If the splash controller is dirty, then we should feed it the current snapshot
        if ( splash_controller.is_dirty() ):

            # Prepare using the current frame buffer data
            splash_controller.prepare(window_controller)

            log2( "Saved splash data", (self.camera.x, self.camera.y), (self.camera.target_x, self.camera.target_y), self.prerender_status )


    # Render the level editor
    def draw_editor(self, tilesheet_sprite, additional_sprites, game_mode, control_center):

        # Quickly check for custom tilesheet.  Overwrite param if we have one!
        if (self.custom_tilesheet):

            # We'll use the custom tilesheet for rendering this universe
            tilesheet_sprite = self.custom_tilesheet


        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the editor controller
        editor_controller = control_center.get_editor_controller()


        # Current zoom scalar
        zoom = editor_controller.zoom_controller.get_interval()

        # Stash current camera position
        (cameraX, cameraY) = (
            int(zoom * self.camera.x),
            int(zoom * self.camera.y)
        )

        """
        # When "zoomed" (showing only background), adjust the camera by scale
        if ( editor_controller.layer_visibility[LAYER_FOREGROUND] == False ):

            # Scale camera position
            (cameraX, cameraY) = (
                int(cameraX / BACKGROUND_MAP_SCALE),
                int(cameraY / BACKGROUND_MAP_SCALE)
            )
        """


        # Render editor grid?
        if (editor_controller.show_grid):

            # Render minor and major grid lines
            for size in (EDITOR_GRID_MINOR_SIZE, EDITOR_GRID_MAJOR_SIZE):

                # Slide around a bit with camera
                (sx, sy) = (
                    -cameraX % size,
                    -cameraY % size
                )

                # Number of grid lines to render
                (linesX, linesY) = (
                    int(SCREEN_WIDTH / size) + int(sx != 0), # Extra line when camera is in-between grid lines
                    int(SCREEN_HEIGHT / size) + int(sy != 0) # SAME
                )

                # Grid line size / color
                (thickness, color) = (
                    2,           # hard-coded
                    (35, 35, 35) # hard-coded
                )

                # Hack to make "major" grid lines stand out better
                if (size == EDITOR_GRID_MAJOR_SIZE):

                    color = (75, 75, 75) # hard-coded

                # Render grid
                for y in range(0, linesY):

                    # X lines first
                    for x in range(0, linesX):

                        # "line"
                        window_controller.get_geometry_controller().draw_rect(sx + (x * size), 0, thickness, SCREEN_HEIGHT, color)

                    # Now the cross line
                    window_controller.get_geometry_controller().draw_rect(0, sy + (y * size), SCREEN_WIDTH, thickness, color)


        for layer in (LAYER_BACKGROUND, LAYER_FOREGROUND):

            # First, render all parallax layer maps that intersect with the current camera position,
            # assuming the parallax layer is visible...
            if ( editor_controller.layer_visibility[layer] ):

                # Assume 1x scale
                scale = 1.0
                parallax = 1.0

                # If the foreground is also visible, then we will render the parallax layer to its true scale
                if ( editor_controller.layer_visibility[LAYER_FOREGROUND] ):

                    # Overwrite
                    scale = SCALE_BY_LAYER[layer]
                    parallax = PARALLAX_BY_LAYER[layer]


                # Overwrite
                scale = zoom * SCALE_BY_LAYER[layer]
                parallax = 1 * PARALLAX_BY_LAYER[layer]


                # Define the visible camera region (just set to the current camera location)
                rPerimeter = (cameraX, cameraY, SCREEN_WIDTH, SCREEN_HEIGHT)

                # Now loop each parallax layer map
                for name in self.map_data[layer]:

                    rRender = self.get_render_region_for_map_on_layer(name, layer, scale = scale, parallax = parallax, zoom = zoom)

                    #print "editor (px, py) = ", (px, py)


                    # If the parallax-adjusted rectangle appears within the present camera location at all,
                    # then we shall render the map.
                    if ( intersect( (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), rRender ) ):

                        # IF the active layer is the foreground layer...
                        if ( editor_controller.active_layer == LAYER_FOREGROUND ):

                            # If this map is the active map, then we'll render it at full color, full opacity, irregardless!
                            if ( name == self.active_map_name ):

                                # This is the map we're on, show it bright!
                                self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (1, 1, 1, 1))

                                # Primary frame
                                window_controller.get_geometry_controller().draw_rect_frame(
                                    rRender[0] - EDITOR_MAP_FRAME_THICKNESS, rRender[1] - EDITOR_MAP_FRAME_THICKNESS, rRender[2] + (2 * EDITOR_MAP_FRAME_THICKNESS), rRender[3] + (2 * EDITOR_MAP_FRAME_THICKNESS), EDITOR_PRIMARY_FRAME_COLOR, EDITOR_MAP_FRAME_THICKNESS
                                )


                            # Otherwise...
                            else:

                                # An inactive map on the active foreground layer...
                                if (layer == LAYER_FOREGROUND):

                                    # If the parallax layer is not visible, then we'll render this inactivate foreground map at full opacity, but dimmed...
                                    if ( not editor_controller.layer_visibility[LAYER_BACKGROUND] ):

                                        # Foreground only, just dim
                                        self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (0.45, 0.45, 0.45, 1))

                                        # Secondary frame, because we're not rendering background (?)
                                        window_controller.get_geometry_controller().draw_rect_frame(
                                            rRender[0] - EDITOR_MAP_FRAME_THICKNESS, rRender[1] - EDITOR_MAP_FRAME_THICKNESS, rRender[2] + (2 * EDITOR_MAP_FRAME_THICKNESS), rRender[3] + (2 * EDITOR_MAP_FRAME_THICKNESS), EDITOR_SECONDARY_FRAME_COLOR, EDITOR_MAP_FRAME_THICKNESS
                                        )

                                    # Otherwise, I'll render this map dimmed with low opacity
                                    else:

                                        # We want to see how the parallax will fit in behind this map
                                        self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (0.45, 0.45, 0.45, 0.45))


                                # An inactive background map while using the foreground layer...
                                elif (layer == LAYER_BACKGROUND):

                                    # Render heavily dimmed, but at full opacity...
                                    self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (0.25, 0.25, 0.25, 1))


                        # If the active layer is the background layer...
                        elif ( editor_controller.active_layer == LAYER_BACKGROUND ):

                            # If this is the active (background) map, then let's render it at full brightness, no matter what
                            if ( name == self.active_map_name ):

                                # This is the map we're on, show it bright!
                                self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (1, 1, 1, 1))

                                # Primary frame
                                window_controller.get_geometry_controller().draw_rect_frame(
                                    rRender[0] - EDITOR_MAP_FRAME_THICKNESS, rRender[1] - EDITOR_MAP_FRAME_THICKNESS, rRender[2] + (2 * EDITOR_MAP_FRAME_THICKNESS), rRender[3] + (2 * EDITOR_MAP_FRAME_THICKNESS), EDITOR_PRIMARY_FRAME_COLOR, EDITOR_MAP_FRAME_THICKNESS
                                )

                            # Otherwise...
                            else:

                                # An inactive map on the active background layer
                                if (layer == LAYER_BACKGROUND):

                                    # If the foreground is visible, then I want to heavily dim this map
                                    if ( editor_controller.layer_visibility[LAYER_FOREGROUND] ):

                                        # Heavily dim
                                        self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (0.25, 0.25, 0.25, 1))

                                    # Otherwise, I'll only kind of dim it
                                    else:

                                        # Heavily dim
                                        self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (0.45, 0.45, 0.45, 1))

                                # An inactive foreground map while editing the background layer...
                                elif (layer == LAYER_FOREGROUND):

                                    # We want to see how the parallax will fit in behind this map
                                    self.draw_map_on_layer_with_explicit_offset(name, layer, rRender[0], rRender[1], tilesheet_sprite, additional_sprites, MODE_EDITOR, control_center, scale = scale, gl_color = (0.45, 0.45, 0.45, 0.45))


                    # When applicable, draw a highlight on the nearest tile on the currently active map...
                    if (name == self.active_map_name):#in self.visible_maps[ self.editor_controller.active_layer ] ):

                        if (layer == editor_controller.active_layer):

                            # Fetch active map
                            m = self.visible_maps[layer][self.active_map_name]

                            # Recall last tile coordinates for the current map
                            (tx, ty) = (
                                editor_controller.mouse.tx,#editor_settings["mouse-tx"],
                                editor_controller.mouse.ty#editor_settings["mouse-ty"]
                            )

                            # Can only paint tiles on the map itself (non-negativei areas)
                            if (tx >= 0 and ty >= 0):

                                # Draw a highlight over the active tile (that we'd paint to)
                                # as long as we aren't dragging anything (map, plane, etc.).
                                if (editor_controller.drag.object_type == ""):

                                    # Calculate zoom-adjusted scale and parallax values
                                    scale = zoom * SCALE_BY_LAYER[layer]
                                    parallax = 1 * PARALLAX_BY_LAYER[layer]

                                    # Get the active map's local screen render region
                                    rRender = self.get_render_region_for_map_on_layer(self.active_map_name, editor_controller.active_layer, scale = scale, parallax = parallax, zoom = zoom)

                                    # Cursor
                                    window_controller.get_geometry_controller().draw_rect_frame(
                                        rRender[0] + int(scale * tx * TILE_WIDTH),
                                        rRender[1] + int(scale * ty * TILE_HEIGHT),
                                        int(scale * TILE_WIDTH),
                                        int(scale * TILE_HEIGHT),
                                        (55, 225, 55),
                                        2
                                    )
                                    #window_controller.get_geometry_controller().draw_rect_frame( (rRender[0] - cameraX) + (tx * TILE_WIDTH), (rRender[1] - cameraY) + (ty * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT, (55, 225, 55), 2)

