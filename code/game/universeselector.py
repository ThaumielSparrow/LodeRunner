import os
import copy

import pygame

from code.extensions.common import UITemplateLoaderExt

from code.render.glfunctions import *

from code.controllers.intervalcontroller import IntervalController

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser

from code.game.universe import Universe

from code.utils.common import is_numeric, xml_encode, xml_decode, get_formatted_time

from code.game.map import Map

from code.constants.common import MODE_GAME, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT
from code.constants.paths import UNIVERSES_PATH

from code.constants.sound import *


# Radius of the spotlight we'll use for each universe's preview maps
PREVIEW_RADIUS = 100

# Padding on either side (left/right) of the preview thing
PREVIEW_PADDING = 20

# Height of any given selection (we'll render a bit of a background / highlight behind the active selection).
OPTION_HEIGHT = int(0.5 * SCREEN_HEIGHT)

# The top and the bottom of the selection screen will "taper" into blackness (gradient)
TAPER_AREA_SIZE = 80


# A wrapper to house data related to the options a player will choose from when selecting universes.
class UniverseSelectorOption:

    def __init__(self, name, title, universe):

        # Track the name of the option (i.e. the universe's name, which folder name we'll return to have loaded)
        self.name = name

        # Track the title of the option (i.e. the universe's title)
        self.title = title


        # If the universe option uses a custom tilesheet, we'll save a reference to that tilesheet here.
        self.custom_tilesheet = None


        # Which type of universe is this?  A story world with connected levels, or linear with singular levels?
        self.type = "story"


        # Last play date
        self.last_played = None

        # Potential autosave path
        self.autosave_path = None


        # How many players does this universe require?
        self.min_players = 1

        # How many players can this universe support?
        self.max_players = 1


        # Any visible subtitles.
        self.subtitles = []


        # An option can contain one or more preview maps.  We'll keep a list of the parameters of any provided preview map.
        self.previews = []

        # Which preview are we currently rendering?  At some point, provided we have more than one, we'll advance to the next.
        self.current_preview = 0


        # As we move from one preview to the next, we'll momentarily render both as we transition from the old one into the new one.
        # to do this, we need to have a stack of "active" preview objects, where we'll store pointers to the preview data houses.
        self.active_previews = []


        # Each option will store completion data for the given universe, according to the most recent save file.
        self.completion_data = {
            "gold-collected": "0",
            "gold-possible": "100",
            "quests-completed": "0",
            "quests-possible": "5",
            "character-level": "2",
            "last-play-date": "???",
            "levels-completed": "0",     # Used for multiplayer
            "levels-possible": "10",
        }


    # Basic configuration
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "title" in options ):
            self.title = options["title"]

        if ( "type" in options ):
            self.type = options["type"]

        if ( "custom-tilesheet" in options ):
            self.custom_tilesheet = options["custom-tilesheet"]


        # For chaining
        return self


    # Configure a piece of completion data
    def set_completion_statistic(self, key, value):

        # Validate
        if (key in self.completion_data):

            # Set
            self.completion_data[key] = value

        else:
            log( "Warning:  Completion statistic '%s' does not exist!" % key )


    # Get a piece of completion data
    def get_completion_statistic(self, key):

        # Validate
        if (key in self.completion_data):

            # Here it is
            return self.completion_data[key]

        else:

            log( "Warning:  Completion statistic '%s' does not exist!" % key )
            return ""


    # Set autosave path
    def set_autosave_path(self, path):

        # Set
        self.autosave_path = path


    # Get autosave path
    def get_autosave_path(self):

        # Return
        return self.autosave_path


    # Add a subtitle
    def add_subtitle(self, subtitle):

        # As many as we want, I guess
        self.subtitles.append(subtitle)


    # Add preview map data, using a given map path as the map data source
    def add_preview(self, path, duration, script, universe):

        # Add a new preview data wrapper
        self.previews.append(
            UniverseSelectorOptionPreview(path, duration, script, universe)
        )


    # Get universe option name
    def get_name(self):

        return self.name


    # Get universe option title
    def get_title(self):

        return self.title


    # Get last played timestamp
    def get_last_played(self):

        # Return timestamp (or None if not previously played)
        return self.last_played


    # Process the option.  Run any active preview, transition to next preview when necessary, loop, etc.
    def process(self):

        # Check to see if we have previews to manage
        if ( len(self.previews) > 0 ):

            # We always need at least one active preview.
            if ( len(self.active_previews) == 0 ):

                # This should only happen on first load.  Let's affirm that we're at preview 0 and clone it into the active preview stack.
                self.current_preview = 0

                # Clone it so that we can return to the original map state later and run the preview again
                self.active_previews.append(
                    self.previews[self.current_preview].clone()
                )

            # If we have one preview, then we will check to see if its time has expired.
            # When it expires, we'll tell it to fade and introduce the next preview.
            elif ( len(self.active_previews) == 1 ):

                # Has the first active preview expired?
                if ( self.active_previews[0].is_expired() ):

                    # Instruct the active preview to begin fading out
                    self.active_previews[0].get_alpha_controller().configure({
                        "target": 0.0
                    })


                    # Now let's step to the next preview index
                    self.current_preview += 1

                    # Wrap around when necessary
                    if ( self.current_preview >= len(self.previews) ):

                        # Infinite preview loop, even if there's just one
                        self.current_preview = 0


                    # Clone that "next" preview onto the top of the active preview stack, creating
                    # a cross-fade effect as we leave one preview and move to the next.
                    self.active_previews.append(
                        self.previews[self.current_preview].clone()
                    )


            # Process each ACTIVE preview (leaving the original "templates" untouched)
            i = 0
            while ( i < len(self.active_previews) ):

                # Basic processing
                self.active_previews[i].process()

                # If this preview has an alpha of 0, then it must be fully faded out.  (If its target were anything but 0,
                # then it would at least be one step above 0 after processing.)  This indicates that we should remove
                # the now completely expired and faded active preview from the active preview stack.
                if ( self.active_previews[i].get_alpha_controller().get_interval() == 0.0 ):

                    # Good knowing ya!
                    self.active_previews.pop(i)

                # Loop
                else:
                    i += 1


    # Render the preview and any title/subtitle data for this option
    def draw_preview(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, control_center, active = True):

        # Quick check to see if this universe option uses a custom tilesheet.
        # Usually this variable is a member of a Universe object, but in this case we're not actively retaining a Universe, just a Map object.
        if (self.custom_tilesheet):

            # Overwrite given tilesheet sprite
            tilesheet_sprite = self.custom_tilesheet


        # Render each active preview
        for preview in self.active_previews:

            # Typically we'll have just one of these.  When we transition from one preview map to the next, though,
            # we'll briefly render then simulatneously using a cross-fade.
            preview.draw(sx, sy, tilesheet_sprite, additional_sprites, text_renderer, control_center, active)


        # Now render a spotlight effect on top of the active preview(s)
        control_center.get_window_controller().get_geometry_controller().draw_exclusive_circle_with_radial_gradient(sx, sy, PREVIEW_RADIUS, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


    # Render any label data above/below the preview
    def draw_labels(self, sx, sy, text_renderer, window_controller, active = True):

        # Render this universe's title above the preview
        if (active):

            # Bright font
            text_renderer.render_with_wrap(self.title, sx - PREVIEW_RADIUS, sy - PREVIEW_RADIUS - int(0.0 * text_renderer.font_height), (225, 225, 225), align = "left")

        else:

            # Dim font
            text_renderer.render_with_wrap(self.title, sx - PREVIEW_RADIUS, sy - PREVIEW_RADIUS - int(0.0 * text_renderer.font_height), (125, 125, 125), align = "left")


    # Render completion data for the given option in a single player universe.  Width and height represents the area we should render within.
    # Return the number of lines we rendered. (?)
    def draw_singleplayer_completion_data(self, sx, sy, width, height, control_center, text_renderer, active = True):

        # Handle to localization controller
        localization_controller = control_center.get_localization_controller()


        # Track rendering position
        (rx, ry) = (
            sx,
            sy
        )

        # Default colors
        (text_normal, text_dim, text_gold) = (
            (225, 225, 225),
            (175, 175, 175),
            (192, 160, 40)
        )

        # Dim everything if this option is not the active selection
        if (not active):

            # Overwrite
            (text_normal, text_dim, text_gold) = (
                (175, 175, 175),
                (125, 125, 125),
                (152, 125, 30)
            )


        # Render label data for story universes
        if (self.type == "story"):

            # Fetch gold collection stats, with some initial assumptions
            (gold_collected, gold_possible, gold_percent) = (
                self.get_completion_statistic("gold-collected"),
                self.get_completion_statistic("gold-possible"),
                "0%" # Assumption
            )

            # Validate that collected / possible data is numeric
            if ( is_numeric(gold_collected) and is_numeric(gold_possible) ):

                # Prevent zero division weirdness
                if ( float(gold_possible) > 0 ):

                    # Update "percent" string to reflect the raw percentage
                    #gold_percent = "%d%%" % int( 100 * ( float(gold_collected) / float(gold_possible) ) )
                    gold_percent = "%s%%" % round(
                        int( (float(gold_collected) / float(gold_possible) + 0.00005) * 10000) / 100.0,
                        2
                    )

                # A universe without gold shouldn't be possible, or practical at least, but if we have one, then I guess we have "all" of that gold...
                else:

                    # Weird!
                    gold_percent = "100%"


            # Fetch quest completion stats, with the same initial assumptions
            (quests_completed, quests_possible, quests_percent) = (
                self.get_completion_statistic("quests-completed"),
                self.get_completion_statistic("quests-possible"),
                "" # Assumption
            )

            # Validate that quest completion data exists / is numeric
            if ( is_numeric(quests_completed) and is_numeric(quests_possible) ):

                # Prevent zero division errors
                if ( float(quests_possible) > 0 ):

                    # Calculate true quest percentage
                    #quests_percent = "%d%%" % int( 100 * ( float(quests_completed) / float(quests_possible) ) )
                    quests_percent = "%s%%" % round(
                        int( (float(quests_completed) / float(quests_possible) + 0.00005) * 10000) / 100.0,
                        2
                    )

                # A universe without quests will not display quest progress... do nothing.
                else:
                    pass


            # Get character level data
            character_level = self.get_completion_statistic("character-level")


            # Assume
            last_play_date = localization_controller.get_label("never")

            # Get last play date data
            if (self.last_played):

                # Format output to human readable
                last_play_date = get_formatted_time(self.last_played)


            # Begin by rendering character level
            ry += text_renderer.render_with_wrap(
                "%s:  %s" % (
                    localization_controller.get_label("character-level:lead-in"),
                    character_level
                ),
                rx,
                ry,
                text_normal
            )

            # Next, render the last play date.  Double space afterwards...
            ry += text_renderer.font_height + text_renderer.render_with_wrap(
                "%s:  %s" % (
                    localization_controller.get_label("last-played:lead-in"), # e.g. "Last Played:  Yesterday"
                    last_play_date
                ),
                rx,
                ry,
                text_dim
            )


            # Now render the universe's general description data, stored as subtitles
            for i in range( 0, len(self.subtitles) ):

                # Render each one as its own paragraph
                ry += text_renderer.render_with_wrap(self.subtitles[i], rx, ry, text_dim, max_width = width)

                # Double-space unless we just rendered the final paragraph
                if ( i < len(self.subtitles) - 1 ):

                    # Formatting
                    ry += text_renderer.font_height


            # The remainder of the data (2 more lines, this is hacked in and all that) shall align to the bottom.
            ry = sy + height - (2 * text_renderer.font_height)

            # If we have no quest data, we can skip that line and just render one line.  Don't model your code after mine.  :)
            if ( quests_percent == "" ):

                # No quest data available leads to an empty-string percentage value, etc.
                ry += text_renderer.font_height


            # If this universe option has quests to complete, render quest completion data.
            # If quests exist, then we will have some data in the "quests percent" string.
            else:

                ry += text_renderer.render_with_wrap("%s:  %s / %s (%s)" % (localization_controller.get_label("quests-finished:lead-in"), quests_completed, quests_possible, quests_percent), rx, ry, text_normal)

            # Render gold completion data, always
            ry += text_renderer.render_with_wrap("%s:  %s / %s (%s)" % (localization_controller.get_label("gold-collected:lead-in"), gold_collected, gold_possible, gold_percent), rx, ry, text_gold)


        # Render label data for linear universes
        elif (self.type == "linear"):

            # Fetch quest completion stats, with the same initial assumptions
            (levels_completed, levels_possible, levels_percent) = (
                self.get_completion_statistic("levels-completed"),
                self.get_completion_statistic("levels-possible"),
                "" # Assumption
            )

            # Validate that quest completion data exists / is numeric
            if ( is_numeric(levels_completed) and is_numeric(levels_possible) ):

                # Prevent zero division errors
                if ( float(levels_possible) > 0 ):

                    # Calculate true quest percentage
                    #levels_percent = "%d%%" % int( 100 * ( float(levels_completed) / float(levels_possible) ) )
                    levels_percent = "%s%%" % round(
                        int( (float(levels_completed) / float(levels_possible) + 0.00005) * 10000) / 100.0,
                        2
                    )

                # A universe without levels will not display level progress... do nothing.
                else:
                    pass


            # Assume
            last_play_date = localization_controller.get_label("never")

            # Get last play date data
            if (self.last_played):

                # Format output to human readable
                last_play_date = get_formatted_time(self.last_played)


            # Here, render the last play date.  Double space afterwards...
            ry += text_renderer.font_height + text_renderer.render_with_wrap(
                "%s:  %s" % (
                    localization_controller.get_label("last-played:lead-in"), # e.g. "Last Played:  Yesterday"
                    last_play_date
                ),
                rx,
                ry,
                text_dim
            )


            # Now render the universe's general description data, stored as subtitles
            for i in range( 0, len(self.subtitles) ):

                # Render each one as its own paragraph
                ry += text_renderer.render_with_wrap(self.subtitles[i], rx, ry, text_dim, max_width = width)

                # Double-space unless we just rendered the final paragraph
                if ( i < len(self.subtitles) - 1 ):

                    # Formatting
                    ry += text_renderer.font_height


            # The remainder of the data (2 more lines, this is hacked in and all that) shall align to the bottom.
            ry = sy + height - (2 * text_renderer.font_height)


            # Always render min/max players.
            if (self.max_players > self.min_players):
                ry += text_renderer.render_with_wrap("%s:  %s - %s" % (localization_controller.get_label("players-allowed:lead-in"), self.min_players, self.max_players), rx, ry, text_normal)

            # Same value, don't render it twice!
            else:
                ry += text_renderer.render_with_wrap("%s:  %s" % (localization_controller.get_label("players-allowed:lead-in"), self.min_players), rx, ry, text_normal)


            # If this universe option has levels to complete, render level completion data.
            # If levels exist, then we will have some data in the "levels percent" string.
            if ( levels_percent != "" ):

                ry += text_renderer.render_with_wrap("%s:  %s / %s (%s)" % (localization_controller.get_label("levels-finished:lead-in"), levels_completed, levels_possible, levels_percent), rx, ry, text_normal)


        # Return the amount of screen space we used while rendering the completion summary
        return (ry - sy)


# A wrapper to house data related to the various map previews we'll display to the player for each option (like a movie trailer, of sorts)
class UniverseSelectorOptionPreview:

    def __init__(self, path, duration, script, universe):

        # Create a generic map object to hold the map data for this preview
        self.map = Map(parent = universe)

        # Load data for the map using the given map path
        self.map.load(
            filepaths = {
                "map": path
            },
            options = {},
            control_center = None # (?) ** I don't need this parameter anymore!
        )


        # How long will it last (in frames)?
        self.duration = duration

        # Which script will we execute when we load the map?  (e.g. on-preview)
        self.script = script


        # Track how long we have been running this preview
        self.timer = 0

        # When a (cloned) preview expires, we'll dismiss it via this alpha controller.
        # When the alpha controller has fully faded, we'll ultimately remove the faded active preview.
        self.alpha_controller = IntervalController(
            interval = 0.0,
            target = 1.0,
            speed_in = 0.025,
            speed_out = 0.025
        )


    # Clone this preview object (used when adding it to the active stack)
    def clone(self):

        return copy.deepcopy(self)


    # Check to see if the timer has met / exceeded the set duration.
    def is_expired(self):

        return (self.timer >= self.duration)


    # Get the alpha controller
    def get_alpha_controller(self):

        return self.alpha_controller


    # Process a preview (essentially just run the timer)
    def process(self):

        # Track timer
        self.timer += 1

        # Process alpha controller
        self.alpha_controller.process()


    # Draw the preview at a given location
    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, control_center, active = True):

        # Offsett the render position by 50% of the map's dimensions to center the map itself
        (rx, ry) = (
            sx - int( self.map.get_width_in_pixels() / 2 ),
            sy - int( self.map.get_height_in_pixels() / 2 )
        )

        # Render the map
        if (active):

            # Full visibility
            self.map.draw(rx, ry, tilesheet_sprite, additional_sprites, MODE_GAME, gl_color = (1, 1, 1, self.alpha_controller.get_interval()), text_renderer = text_renderer, control_center = control_center)

        else:

            # Dim
            self.map.draw(rx, ry, tilesheet_sprite, additional_sprites, MODE_GAME, gl_color = (1, 1, 1, float( self.alpha_controller.get_interval() / 2 )), text_renderer = text_renderer, control_center = control_center)


# An object that allows the player to view all of the universes with previews and metadata
# and decide which one they want to begin / resume.
class UniverseSelector(UITemplateLoaderExt):

    def __init__(self, show_singleplayer = True, show_multiplayer = False, resume_game = False):

        UITemplateLoaderExt.__init__(self)


        # Should we show single-player universes?
        self.show_singleplayer = show_singleplayer

        # How about multiplayer universes?
        self.show_multiplayer = show_multiplayer


        # When we select a universe, will we begin a new game, or will we resume the most recent save we can find?
        self.resume_game = resume_game


        # Keep a list of the universes that match the given parameters
        self.matches = self.find_matching_universe_names(show_singleplayer, show_multiplayer)


    # Find any universe that matches the given single/multi qualifications, according to each universe's meta file.
    # If no meta file exists, the universe shall not match either parameter.
    def find_matching_universe_names(self, show_singleplayer, show_multiplayer):

        # Track matches
        matches = []


        # Validate that universe data exists
        if ( os.path.exists(UNIVERSES_PATH) ):

            # Query all folders (ok, files and folders, which we'll loop only folders).
            # Each universe has its own folder.
            for name in os.listdir(UNIVERSES_PATH):

                # We only care about folders
                if ( os.path.isdir( os.path.join(UNIVERSES_PATH, name) ) ):

                    # We must find the meta file for this universe
                    metadata_path = os.path.join( UNIVERSES_PATH, name, "meta.xml" )

                    # If it doesn't exist, then this universe does not exist, on the record
                    if ( os.path.exists(metadata_path) ):

                        # The metadata uses the xml format
                        f = open(metadata_path, "r")
                        xml = f.read()
                        f.close()

                        # Let's parse the metadata xml
                        root = XMLParser().create_node_from_xml(xml).find_node_by_tag("metadata")

                        # Validate
                        if (root):

                            # Find the min/max player count.  Start with assumed defaults.
                            (min_players, max_players) = (1, 1) # Assumption

                            # Universe type (story or linear)
                            universe_type = "story"


                            # Read in given min players data
                            node = root.find_node_by_id("min-players")

                            # Validate
                            if (node):

                                # Cast as int
                                min_players = int( node.innerText )


                            # Read in given max players data
                            node = root.find_node_by_id("max-players")

                            # Read in given max players data
                            if (node):

                                # Cast as int
                                max_players = int( node.innerText )


                            # Check for type param
                            node = root.find_node_by_id("type")

                            # Validate
                            if (node):

                                # Grab type param
                                universe_type = node.innerText


                            # Does this universe work for a single player game?  And if so, do we want such universes?
                            if ( (show_singleplayer) and (min_players < 2) ):

                                # Add it to our list of results
                                matches.append( (name, universe_type, min_players, max_players) )


                            # Does this universe work for a multiplayer game?  And if so, do we want multiplayer universes?
                            if ( (show_multiplayer) and (max_players > 1) ):

                                # In case we're querying for both single AND multiplayer universes, let's check for duplicates.
                                if ( not (name in matches) ):

                                    # Add the universe's name to our list of results
                                    matches.append( (name, universe_type, min_players, max_players) )


        # Return the list of matching universe names
        return matches


    # Based on the current set of matching universe names, present the player with the various universes
    # they can choose from.  If we're looking at single-player universes only, we'll show overall completion status.
    # If we're looking at multiplayer only, we'll show how many levels they've completed.  If we're looking at both,
    # we'll show no completion data at all.
    def select(self, tilesheet_sprite, additional_sprites, control_center, universe):

        # Prepare a list of options (all of the universes)
        options = []


        # Track the current cursor selection
        current_option = 0

        # Once we make a selection, we will lock the cursor in place as the window fades.
        cursor_locked = False

        # When we move from one option to another, we'll instantly move the cursor (for selection logic),
        # but the player will see a gradual scroll.
        current_scroll = 0


        # Each universe will have a set of "preview" maps that give the user a visual indicator / reminder of the universe
        # they are looking at.  Also, each universe will (likely) provide some bit of completion data to the user.
        for (name, universe_type, min_players, max_players) in self.matches:

            # First, let's again load the metadata for this universe to prepare label data
            metadata_path = os.path.join( UNIVERSES_PATH, name, "meta.xml" )

            # Validate
            if ( os.path.exists(metadata_path) ):

                # Create a temporary Universe object for this universe match.
                # Note that we're only loading in the metadata for this universe; we're not going to use it for any gameplay / rendering logic.
                u = Universe(name, MODE_GAME, control_center, meta_only = True)

                # I want to borrow the player name session variable from the provided Universe object
                u.get_session_variable("core.player1.name").set_value(
                    universe.get_session_variable("core.player1.name").get_value()
                )


                # Assume we have never played this universe
                last_played = None


                # Before we read in the metadata, let's check for a lastplayed.txt file via
                # the given universe's save path.
                path = os.path.join( u.get_working_save_data_path(), "lastplayed.txt" )

                # File exists?
                if ( os.path.exists(path) ):

                    # We'll read in the last played string from that file.  Shame on the user that modifies it!
                    f = open(path, "r")
                    last_played = float( f.readline() ) # Heck, why read more than one line?  Crazy users!
                    f.close()


                # Read in xml content
                f = open(metadata_path, "r")
                xml = f.read()
                f.close()

                # Parse xml
                root = XMLParser().create_node_from_xml(xml).find_node_by_tag("metadata")


                # Default universe title to the folder name
                title = name

                # See if the metadata defines the formal readable title
                node = root.find_node_by_id("title")

                # Validate
                if (node):

                    # Use the given title
                    title = node.innerText


                # Let's create a new option wrapper using the name/title data
                option = UniverseSelectorOption(name, title, u)


                # Set the type param
                option.configure({
                    "type": universe_type,
                    "custom-tilesheet": u.custom_tilesheet  # Universe option might or might not use a custom tilesheet
                })


                # Update last played data
                option.last_played = last_played


                # Update min/max players for this option
                option.min_players = min_players
                option.max_players = max_players


                # For story universes, I want to load the most recent save, I think... ?
                if (universe_type == "story"):

                    # Generate autosave location
                    path = os.path.join( u.get_working_save_data_path(), "autosave1" )

                    # Does that save path exist?
                    # Has the user previously played on this story mode?
                    if ( os.path.exists(path) ):

                        # Disabled - I'm not showing "in progress" stats, am I?
                        """
                        # Debug - go with checkpoint for 
                        control_center.get_save_controller().load_from_folder(
                            os.path.join( u.get_working_save_data_path(), "autosave1" ),
                            control_center,
                            u,
                            data_only = True     # Don't build the active map when loading the data
                        )
                        """

                        # Set the autosave path for this option
                        option.set_autosave_path(path)


                    # Set completion statistics.
                    # Note that we only do this for story universes; linear universes never render these particular data to the user...
                    option.set_completion_statistic( "gold-collected", "%d" % 0 )#u.count_collected_gold_pieces("overworld") )
                    option.set_completion_statistic( "gold-possible", "%d" % u.count_gold_pieces("overworld") )

                    # Set character level
                    option.set_completion_statistic( "character-level", "%s" % 1 )#u.get_session_variable("core.player1.level").get_value() )

                    # Set quests completed, possible
                    option.set_completion_statistic( "quests-completed", "%d" % 0 )#u.count_completed_quests() )
                    option.set_completion_statistic( "quests-possible", "%d" % u.count_quests() )

                # For linear universes, I want to loop through the selectable levels node
                # to get a completion / total count.
                elif (universe_type == "linear"):

                    # Create a temporary Universe object so that we can run some analysis
                    #universe = Universe(name, MODE_GAME, control_center)

                    # Load the single autosave (autosave slot 1) we always use for linear universes
                    control_center.get_save_controller().load_from_folder(
                        os.path.join( u.get_working_save_data_path(), "autosave1" ),
                        control_center,
                        u,
                        data_only = True    # Don't build active map
                    )


                    # Count how many levels the player has completed, out of the total number of levels...
                    (levels_completed, levels_found) = (0, 0)

                    # Find selectable levels node
                    ref_selectable_levels = root.find_node_by_tag("selectable-levels")

                    # Validate
                    if (ref_selectable_levels):

                        # Loop listed levels
                        for ref_selectable_level in ref_selectable_levels.get_nodes_by_tag("selectable-level"):

                            # Grab map data for this map
                            map_data = u.get_map_data( ref_selectable_level.innerText )

                            # Validate that we have a known map for the matched universe
                            if (map_data):

                                # Count denominator
                                levels_found += 1

                                # Complete?
                                if ( map_data.is_map_completed() ):

                                    # Increment numerator
                                    levels_completed += 1


                    # Update option params, casting them as strings.
                    option.set_completion_statistic("levels-completed", "%d" % levels_completed)
                    option.set_completion_statistic("levels-possible", "%d" % levels_found)


                # See if we can find any subtitle data (i.e. general universe description / advertisement)
                ref_subtitles = root.find_node_by_tag("subtitles")

                # Validate
                if (ref_subtitles):

                    # Loop each subtitle
                    for ref_subtitle in ref_subtitles.get_nodes_by_tag("subtitle"):

                        # Add the subtitle to this universe option
                        option.add_subtitle(
                            ref_subtitle.innerText
                        )


                # Now check for any given map preview data for this universe.  Ordinarily, we'll loop through each given
                # preview map, rendering it with a spotlight effect and running a given script on map load.
                ref_preview_maps = root.find_node_by_tag("preview-maps")

                # Validate
                if (ref_preview_maps):

                    # Find each given preview map
                    for ref_preview in ref_preview_maps.get_nodes_by_tag("preview-map"):

                        # Default assumptions for this preview map
                        (map_name, duration, measure, script) = (
                            None, # Don't assume any map.
                            3, # Assume duration of 3
                            "seconds", # 3 seconds, that is
                            "on-preview" # Typically we call a script named "on-preview"
                        )


                        # Check for specified duration
                        if ( ref_preview.has_attribute("duration") ):

                            # Grab value
                            value = ref_preview.get_attribute("duration")

                            # Must be numeric
                            if ( is_numeric(value) ):

                                # Overwrite, cast as float
                                duration = float(value)


                        # Check for specified duration measure
                        if ( ref_preview.has_attribute("measure") ):

                            # Overwrite value
                            measure = ref_preview.get_attribute("measure")


                        # Check for onload script overwrite
                        if ( ref_preview.has_attribute("script") ):

                            # Overwrite
                            script = ref_preview.get_attribute("script")


                        # Before we wrap the data, let's convert the duration into frames.
                        if (measure == "seconds"):

                            # 60fps (hard-coded)
                            duration = int(duration * 60)

                        # Default to frames
                        else:

                            # Retain original value, but cast it into an int
                            duration = int(duration)


                        # Get the given map name
                        map_name = ref_preview.innerText


                        # Let's validate that the universe contains a map by that name
                        path = os.path.join( UNIVERSES_PATH, name, "maps", "%s.xml" % map_name )

                        # Validate
                        if ( os.path.exists(path) ):

                            # Add this preview data to the universe option's list of previews
                            option.add_preview(path, duration, script, u)


                # Add the new option to our list of universe options
                options.append(option)


        # Inline function (rarely use these!) for sorting.
        # This will be a two-column sort, sorting first on "group" (story1/coop101, played, unplayed...),
        # and then sorting within that group by last played, descending...
        def f_sort(option):

            # Assume a rank of "2" for the first column, indicating an unplayed universe...
            col1 = 2

            # Here's where we hard-code the main story mode.  If this option points to "story1,"
            # then we give col1 a rank of "1."  Rank of one beats all rank 2, but it won't beat rank 0 (i.e. previously played universe).
            # Same logic will apply to "coop 101" universe.
            if ( option.get_name() in ("story1", "coop101") ):

                # Set rank to "1"
                col1 = 1


            # Assume we haven't played this universe, setting col2 to a default rank of "0."
            # (We're going to make all timestamps negative, which means that this "0" is the "worst" rank, the last rank in an ascending sort.)
            col2 = 0

            # Check for a "last played" timestamp
            if ( option.get_last_played() != None ):

                # We now improve column 1's rank to "0," the group of previously played universes.
                col1 = 0

                # We will give column 2 a rank below 0, the opposite of the timestamp.
                # This means that the most recently played universe (highest timestamp value) will take the lowest value ("largest" negative), putting
                # it in position to take the first slot in the ascending sort.
                col2 = -1 * option.get_last_played()


            # Return two-column sort...
            return (col1, col2)


        # Sort the list of options we've put together (now including last play date).  We prefer to show the most recently played universes first.
        # Second, we prefer to show "story1" first, if it has not yet been played.  (Otherwise, we simply base its sort on last play date.)
        # After that, we order by universe name, alphabetically.)
        options = sorted(
            options, key = lambda option: f_sort(option)
        )


        # As we move into the block that renders all of the options, we're going to want a couple of shortcuts to some of the controllers.
        window_controller = control_center.get_window_controller()

        # Handle to the input controller
        input_controller = control_center.get_input_controller()

        # Obviously we'll have text to draw
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()

        # Let's grab the scissor controller as well
        scissor_controller = control_center.get_window_controller().get_scissor_controller()



        # Now let's do one last thing:  I want to load in a Ui widget to serve as the "backdrop" for this
        # selector page.  It's just a header, like on the main menu, except we'll scroll it away as we move
        # from one universe option to another.
        # Fetch the widget dispatcher
        template = self.fetch_xml_template( "universeselector.backdrop", version = "singleplayer" if (self.show_singleplayer) else "multiplayer" ).add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % int(PAUSE_MENU_Y / 2) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create the local backdrop widget
        backdrop_widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, None)
        backdrop_widget.set_id("universeselector-backdrop")
        #self.backdrop_widget.focus()


        # Create a variable where we can optionally store
        # an "are you sure?" prompt for storyline universes.
        warning_widget = None


        # FPS timer
        clock = pygame.time.Clock()

        # Select loop
        while True:

            # Target 60fps (hard-coded)
            clock.tick(60)

            # Clear backbuffer
            #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            clear_buffers()

            # Clear to black
            window_controller.get_geometry_controller().draw_rect(0, 0, window_controller.render_width, window_controller.render_height, (0, 0, 0))


            # Poll keyboard input
            (events, keypresses) = (
                pygame.event.get(),
                pygame.key.get_pressed()
            )

            # Feed input controller
            input_controller.poll_and_update_system_input(events, keypresses)
            input_controller.poll_and_update_gameplay_input( input_controller.get_system_input(), keypresses )

            # Read back abstracted input data
            system_input = input_controller.get_system_input()
            gameplay_input = input_controller.get_gameplay_input()


            # ** Debug - Abort
            if ( (K_F11 in input_controller.get_system_input()["keydown-keycodes"]) ):
                return "asdf?"
            if ( (K_F12 in input_controller.get_system_input()["keydown-keycodes"]) ):
                log( 5/0 )


            # Create an event queue
            results = EventQueue()


            # If we haven't yet made a selection, we will check for cursor control.
            # We also ignore selector input if the user is viewing the "resume game?" warning widget.
            if ( (not cursor_locked) and (warning_widget == None) ):

                # Perhaps the user wants to cancel, go back to the menu without selecting any universe?
                if (
                    (K_ESCAPE in input_controller.get_system_input()["keydown-keycodes"]) or
                    ( input_controller.check_gameplay_action("escape", system_input, [], True) )
                ):

                    # Lock cursor, no point in checking input now...
                    cursor_locked = True

                    # App fade, followed by a "cancel" event on this selector
                    window_controller.fade_out(
                        on_complete = "universeselector:cancel"
                    )

                # Cursor up?
                elif (INPUT_SELECTION_UP in gameplay_input):

                    # Move up one
                    current_option -= 1

                    # Wrap around?
                    if (current_option < 0):

                        # Bottom of the list
                        current_option = len(options) - 1

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Cursor down?
                elif (INPUT_SELECTION_DOWN in gameplay_input):

                    # Move down one
                    current_option += 1

                    # Wrap around?
                    if ( current_option >= len(options) ):

                        # To the top!
                        current_option = 0

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Home key?
                elif (INPUT_SELECTION_HOME in gameplay_input):

                    # Top of the list
                    current_option = 0

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # End key?
                elif (INPUT_SELECTION_END in gameplay_input):

                    # End of the list
                    current_option = ( len(options) - 1 )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Page up?
                elif (INPUT_SELECTION_PAGEUP in gameplay_input):

                    # Let's move up by 2, that's about how many fit on a page
                    current_option -= 2

                    # Don't wrap
                    if (current_option < 0):

                        # Clamp
                        current_option = 0

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Page down?
                elif (INPUT_SELECTION_PAGEDOWN in gameplay_input):

                    # Go down by 2, that's about how many fit on a page
                    current_option += 2

                    # Don't wrap
                    if ( current_option >= len(options) ):

                        # Clamp
                        current_option = ( len(options) - 1 )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Select current universe option?
                elif (INPUT_SELECTION_ACTIVATE in gameplay_input):

                    # Does this universe have an existing autosave path?
                    if ( options[current_option].get_autosave_path() != None ):

                        # Get the template for the warning widget
                        template = self.fetch_xml_template("mainmenu.root.story.warning").add_parameters({
                            "@x": xml_encode( "%d" % PAUSE_MENU_X ), # hard-coded
                            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
                            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ) # hard-coded
                        })

                        # Compile template
                        root = template.compile_node_by_id("dialog")

                        # Create widget
                        warning_widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)
                        warning_widget.set_id("mainmenu.root.story.warning")

                        # Find the info widget (left pane).
                        # Find the options widget (right pane).
                        (left, right) = (
                            warning_widget.find_widget_by_id("info"),
                            warning_widget.find_widget_by_id("menu")
                        )

                        # Left pane slides in from the left
                        left.slide(DIR_LEFT, int(PAUSE_MENU_WIDTH / 2), animated = False)
                        left.slide(None)

                        # Right pane slides in from the right!
                        right.slide(DIR_RIGHT, int(PAUSE_MENU_WIDTH / 2), animated = False)
                        right.slide(None)

                    # If not, then we can immediately return the universe name (well, after a fade...)
                    else:

                        # Fade the app window, raising a special-case escape event when done.
                        window_controller.fade_out(
                            on_complete = "universeselector:escape"
                        )

                        # Lock future cursor movement as we fade out
                        cursor_locked = True

                        # Select sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_SELECT)


            # The scroll should always target the current option
            scroll_target = (current_option * OPTION_HEIGHT)


            # Need to scroll up?
            if (current_scroll > scroll_target):

                # Calculate ideal scroll pace
                dy = max(
                    20,
                    int( (current_scroll - scroll_target) / 10 )
                )

                # Scroll
                current_scroll -= dy


                # Don't overshoot
                if (current_scroll < scroll_target):

                    # Align
                    current_scroll = scroll_target

            # Need to scroll down?
            elif (current_scroll < scroll_target):

                # Calculate ideal scroll pace
                dy = max(
                    20,
                    int( (scroll_target - current_scroll) / 10 )
                )

                # Scroll
                current_scroll += dy


                # Don't overshoot
                if (current_scroll > scroll_target):

                    # Align
                    current_scroll = scroll_target


            # Let's process (alpha only, really) the backdrop widget
            backdrop_widget.process(control_center, None) # (?) No universe?

            # Go ahead and draw the backdrop widget, scrolling it off of the screen as we move down the list...
            backdrop_widget.draw(0, 0 - current_scroll, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


            # Loop through each available option
            for i in range( 0, len(options) ):

                #print "%d - %s" % (i, options[i].name)
                #text_renderer.render_with_wrap( "%d - %s" % (i, options[i].name), 5, 5 + (i * text_renderer.font_height), (225, 225, 25))

                # Process the option (alpha / preview logic)
                options[i].process()

                (sx, sy) = (
                    PAUSE_MENU_X + PREVIEW_PADDING,
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + (i * OPTION_HEIGHT) - (current_scroll)
                )

                scissor_controller.push( (sx, sy, 2 * PREVIEW_RADIUS, 2 * PREVIEW_RADIUS) )


                # Render the option centered on the screen
                options[i].draw_preview( sx + PREVIEW_RADIUS, sy + PREVIEW_RADIUS, tilesheet_sprite, additional_sprites, text_renderer, control_center, active = (i == current_option) )

                scissor_controller.pop()


            for i in range( 0, len(options) ):

                (sx, sy) = (
                    PAUSE_MENU_X + PREVIEW_RADIUS + PREVIEW_PADDING,
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + (i * OPTION_HEIGHT) - (current_scroll)
                )

                indent = 0
                if ( i == current_option ):

                    indent = 10

                # If this is the current option (if and only if), then we shall render the title of the universe above the glow area.
                # We'll render it independent of scrolling action (just like the glow area), perhaps as an indicator that they can hit enter immediately??
                if (i == current_option):

                    # Yeah, I'm indenting by the font height.  I just want a little margin...
                    text_renderer.render_with_wrap( "\"%s\"" % options[i].get_title(), PAUSE_MENU_X + text_renderer.font_height, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2) - int(1.1 * text_renderer.font_height), (225, 225, 225) )
                    #options[i].draw_labels( indent + sx, sy + PREVIEW_RADIUS, text_renderer, window_controller, active = (i == current_option) )


                (sx, sy) = (
                    PAUSE_MENU_X + (2 * PREVIEW_RADIUS) + (2 * PREVIEW_PADDING),
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + (i * OPTION_HEIGHT) - (current_scroll)
                )

                options[i].draw_singleplayer_completion_data( indent + sx, sy, PAUSE_MENU_WIDTH - ((2 * PREVIEW_RADIUS) + (2 * PREVIEW_PADDING)), (2 * PREVIEW_RADIUS), control_center, text_renderer, active = (i == current_option) )


            #text_renderer.render_with_wrap("Try to collect all of the gold in this story while avoiding all of the bad guys!", int(0.75 * SCREEN_WIDTH), int(SCREEN_HEIGHT / 2), (175, 175, 175), max_width = int(0.5 * SCREEN_WIDTH), align = "center")


            # Does the warning widget exist?
            if (warning_widget):

                # Process it, pulling in the returned events
                results.append(
                    warning_widget.process(control_center, None)
                )

                # Because I'm hacking this widget in outside of any Menu object,
                # I have to handle input manually.
                if (
                    (warning_widget.alpha_controller.get_target() > 0) and
                    (warning_widget.alpha_controller.get_interval() > 0.5) # Brutally hacky way to avoid double-return (i.e. instant selection)
                ):

                    results.append(
                        warning_widget.handle_user_input(control_center, None)
                    )

                """
                if (gameplay_input != []):
                    a = input_controller.get_gameplay_input()
                    b = input_controller.get_gameplay_input()
                    c = input_controller.get_gameplay_input()
                    print (gameplay_input, a, b, c)
                    sys.exit()
                """

                # Render it centered
                warning_widget.draw(0, 0, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


            # ...
            window_controller.get_geometry_controller().draw_rect(PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), PAUSE_MENU_WIDTH, OPTION_HEIGHT, (225, 225, 225, 0.075))

            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), int(0.25 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.05), (225, 225, 225, 0.25) )
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X + int(0.25 * PAUSE_MENU_WIDTH), int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), int(0.75 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.25), (225, 225, 225, 0.05) )

            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) + int(OPTION_HEIGHT / 2) - 2, int(0.25 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.05), (225, 225, 225, 0.25) )
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X + int(0.25 * PAUSE_MENU_WIDTH), int(SCREEN_HEIGHT / 2) + int(OPTION_HEIGHT / 2) - 2, int(0.75 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.25), (225, 225, 225, 0.05) )


            # Render "tapering" effect
            #window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, 0, SCREEN_WIDTH, TAPER_AREA_SIZE, (0, 0, 0, 1.0), (0, 0, 0, 0.0))
            window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, (SCREEN_HEIGHT - TAPER_AREA_SIZE), SCREEN_WIDTH, TAPER_AREA_SIZE, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


            # Process window controller
            results.append(
                window_controller.process(control_center, None) # (?) no universe? ??? #some_universe) some_universe? ? ?
            )

            # Application-level fade control
            if ( window_controller.alpha_controller.get_interval() < 1.0 ):

                window_controller.render_fade_using_alpha_controller(
                    window_controller.fade_mode,
                    window_controller.alpha_controller
                )


            # Handle events
            event = results.fetch()

            # Loop all
            while (event):

                # Convenience
                action = event.get_action()


                # Special case - exit universe selector
                if ( action == "universeselector:escape" ):

                    # Return the name of the universe selection we made
                    return options[current_option].get_name()

                # Special case - exit universe selector, but also
                # attach a "resume:" prefix.
                elif ( action == "universeselector:escape:resume" ):

                    # Return the name with a prefix
                    return "resume:%s" % options[current_option].get_name()

                # Special case - cancel universe selector
                elif ( action == "universeselector:cancel" ):

                    # Return nothing, indicating that we did not select any universe (i.e. just go back to the menu)
                    return None

                # Resume a previous autosave?  (From warning widget)
                elif ( action == "warning:resume" ):

                    # Find the info widget (left pane).
                    # Find the options widget (right pane).
                    (left, right) = (
                        warning_widget.find_widget_by_id("info"),
                        warning_widget.find_widget_by_id("menu")
                    )

                    # Left pane slides away to the left
                    left.slide(DIR_LEFT, int(PAUSE_MENU_WIDTH / 2), animated = True)

                    # Right pane slides away to the right
                    right.slide(DIR_RIGHT, int(PAUSE_MENU_WIDTH / 2), animated = True)

                    # Fade the app window, raising a special-case escape
                    # AND resume event when done.
                    window_controller.fade_out(
                        on_complete = "universeselector:escape:resume"
                    )

                    # Lock future cursor movement as we fade out
                    cursor_locked = True

                # Begin a new adventure?  (From warning widget.  Overwrites existing autosave!)
                elif ( action == "warning:new" ):

                    # Find the info widget (left pane).
                    # Find the options widget (right pane).
                    (left, right) = (
                        warning_widget.find_widget_by_id("info"),
                        warning_widget.find_widget_by_id("menu")
                    )

                    # Left pane slides away to the left
                    left.slide(DIR_LEFT, int(PAUSE_MENU_WIDTH / 2), animated = True)

                    # Right pane slides away to the right
                    right.slide(DIR_RIGHT, int(PAUSE_MENU_WIDTH / 2), animated = True)

                    # Fade the app window, raising a special-case escape event when done.
                    window_controller.fade_out(
                        on_complete = "universeselector:escape"
                    )

                    # Lock future cursor movement as we fade out
                    cursor_locked = True

                # Do nothing (from warning widget)
                elif ( action == "warning:cancel" ):

                    # Find the info widget (left pane).
                    # Find the options widget (right pane).
                    (left, right) = (
                        warning_widget.find_widget_by_id("info"),
                        warning_widget.find_widget_by_id("menu")
                    )

                    # Left pane slides away to the left
                    left.slide(DIR_LEFT, int(PAUSE_MENU_WIDTH / 2), animated = True)

                    # Right pane slides away to the right
                    right.slide(DIR_RIGHT, int(PAUSE_MENU_WIDTH / 2), animated = True)

                    # Fade the warning widget, killing it upon its disappearance
                    # to re-allow universe selection input.
                    warning_widget.hide(
                        on_complete = "warning:kill"
                    )

                # Kill warning widget
                elif ( action == "warning:kill" ):

                    # Set widget object to null
                    warning_widget = None

                # Right now, I don't expect to handle anything except for this generic "leave selector" event.
                else:
                    pass


                # Loop
                event = results.fetch()


            # Render newsfeeder items on top of even the fade effect
            #window_controller.newsfeeder.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], window_controller)


            # Show backbuffer
            pygame.display.flip()

            # Run sound controller processing (sound effects, background track looping, etc.)
            control_center.get_sound_controller().process(universe)
