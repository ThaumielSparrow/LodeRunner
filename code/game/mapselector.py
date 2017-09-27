import os
import copy

import pygame

from code.extensions.common import UITemplateLoaderExt

from code.render.glfunctions import *

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser

from code.utils.common import is_numeric, xml_encode, xml_decode, format_framecount_as_time

from code.game.map import Map

from code.constants.common import MODE_GAME, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, GENUS_PLAYER, GENUS_RESPAWN_PLAYER
from code.constants.states import STATUS_INACTIVE

from code.constants.paths import UNIVERSES_PATH

from code.constants.sound import *


# Number of levels to place on each row in the map selector
PER_ROW = 2

# Padding between columns
COLUMN_PADDING = 20


# Radius of the spotlight we'll use for each universe's preview maps
PREVIEW_RADIUS = 100

# Padding on either side (left/right) of the preview thing
PREVIEW_PADDING = 20

# Width of any given selection
OPTION_WIDTH = int( (PAUSE_MENU_WIDTH - ((PER_ROW - 1) * COLUMN_PADDING)) / PER_ROW )

# Height of any given selection (we'll render a bit of a background / highlight behind the active selection).
OPTION_HEIGHT = int(0.5 * SCREEN_HEIGHT)

# The top and the bottom of the selection screen will "taper" into blackness (gradient)
TAPER_AREA_SIZE = 80


# A wrapper to house data related to the options a player will choose from when selecting universes.
class MapSelectorOption:

    def __init__(self, name, title):

        # Track the name of the option (i.e. the map's name, which folder name we'll return to have loaded)
        self.name = name

        # Track the title of the option (i.e. the map's title)
        self.title = title


        # Each option will store completion data for the given universe, according to the most recent save file.
        self.completion_data = {
            "gold-collected": "0",
            "gold-possible": "100",
            "quests-completed": "0",
            "quests-possible": "5",
            "character-level": "2",
            "last-play-date": "???",
            "levels-complete": "0", # Used for multiplayer
            "levels-possible": "10",
            "best-completion-time": "--:--",        # Best time in which the player has completed a given level
            "level-index": 1,                       # Which level is this, in the sequence of levels for a linear universe?
            "level-count": 20                       # How many levels does the linear universe contain?
        }


    # Basic configuration
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "title" in options ):
            self.title = options["title"]

        if ( "best-completion-time" in options ):
            self.set_completion_statistic( "best-completion-time", options["best-completion-time"] )

        if ( "level-index" in options ):
            self.set_completion_statistic( "level-index", options["level-index"] )

        if ( "level-count" in options ):
            self.set_completion_statistic( "level-count", options["level-count"] )

        # For chaining
        return self


    # Get map name
    def get_name(self):

        # Return
        return self.name


    # Get option title
    def get_title(self):

        # Return
        return self.title


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


    # Add a subtitle
    def add_subtitle(self, subtitle):

        # As many as we want, I guess
        self.subtitles.append(subtitle)


    # Create preview map data, using a given map path as the map data source
    def create_preview(self, path, universe):

        # Create the single preview object
        self.preview = MapSelectorOptionPreview(path, 0, "no-script", universe)

        # Return new preview object
        return self.preview


    # Get universe option name
    def get_name(self):

        return self.name


    # Get universe option title
    def get_title(self):

        return self.title


    # Process the option.  Run any active preview, transition to next preview when necessary, loop, etc.
    def process(self, active, control_center, universe):

        # Check to see if we have a preview to manage
        if (self.preview):

            # Process the map preview
            self.preview.process(active, control_center, universe)


    # Render the preview and any title/subtitle data for this option
    def draw_preview(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller, active = True):

        # Render the preview, if/a
        if (self.preview):

            # Render
            self.preview.draw(sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller, active)


        # Now render a spotlight effect on top of the active preview(s)
        window_controller.get_geometry_controller().draw_exclusive_circle_with_radial_gradient(sx, sy, PREVIEW_RADIUS, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


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
    def draw_singleplayer_completion_data(self, sx, sy, width, height, text_renderer, active = True):

        # Track rendering position
        (rx, ry) = (
            sx,
            sy
        )


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
                gold_percent = "%d%%" % int( 100 * ( float(gold_collected) / float(gold_possible) ) )

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
                quests_percent = "%d%%" % int( 100 * ( float(quests_completed) / float(quests_possible) ) )

            # A universe without quests will not display quest progress... do nothing.
            else:
                pass


        # Get character level data
        character_level = self.get_completion_statistic("character-level")

        # Get last play date data
        last_play_date = self.get_completion_statistic("last-play-date")


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


        # All data (2 lines, this is hacked in and all that) shall align to the bottom.
        ry = sy + height - (2 * text_renderer.font_height)


        # Render map completion status
        ry += text_renderer.render_with_wrap("Best Time: %s" % self.get_completion_statistic("best-completion-time"), rx, ry, text_normal)

        # Render ... what?
        ry += text_renderer.render_with_wrap("Level %s of %s" % (self.get_completion_statistic("level-index"), self.get_completion_statistic("level-count")), rx, ry, text_normal)


        # Return the amount of screen space we used while rendering the completion summary
        return (ry - sy)


# A wrapper to house data related to the various map previews we'll display to the player for each option (like a movie trailer, of sorts)
class MapSelectorOptionPreview:

    def __init__(self, path, duration, script, universe):

        # Remember the map's filepath in case we need to reload it (for looping replays)
        self.path = path


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


        # Overwrite map type as "gif" to prevent autosaves, etc.
        self.map.set_type("gif")


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


    # Get the alpha controller
    def get_alpha_controller(self):

        return self.alpha_controller


    # Get the preview's Map object
    def get_map(self):

        return self.map


    # Process a preview (essentially just run the timer)
    def process(self, active, control_center, universe):

        # Process alpha controller
        self.alpha_controller.process()


        # Should we run map / replay logic for this preview?
        if (active):

            # Lock all input (we don't want the player's key movements affecting the GIFs!)
            control_center.get_input_controller().lock_all_input()

            #"""
            # Lock universe camera
            universe.get_camera().lock()

            # Process universe game logic
            #universe.process_game_logic(control_center)

            """
            # Process the active map's replay data
            m = self.get_map()
            m.process_replay_data(control_center, universe)
            m.process(control_center, universe)
            m.process_drama(control_center, universe)
            # Do we need to play any sound effect?
            #sfx_keys = m.process_sound()
            #for sfx_key in sfx_keys:
            #    self.sound_effects[sfx_key].play()
            m.post_process(control_center, universe)
            """

            # Unlock camera
            universe.get_camera().unlock()


            # Unlock input
            control_center.get_input_controller().unlock_all_input()


    # Draw the preview at a given location
    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller, active = True):

        # Offset the render position by 50% of the map's dimensions to center the map itself
        (rx, ry) = (
            sx - int( self.map.get_width_in_pixels() / 2 ),
            sy - int( self.map.get_height_in_pixels() / 2 )
        )

        # Render the map
        if (active):

            # Full visibility
            self.map.draw(rx, ry, tilesheet_sprite, additional_sprites, MODE_GAME, gl_color = (1, 1, 1, self.alpha_controller.get_interval()), text_renderer = text_renderer, window_controller = window_controller)

        else:

            # Dim
            self.map.draw(rx, ry, tilesheet_sprite, additional_sprites, MODE_GAME, gl_color = (1, 1, 1, float( self.alpha_controller.get_interval() / 2 )), text_renderer = text_renderer, window_controller = window_controller)


# An object that allows the player to view all of the universes with previews and metadata
# and decide which one they want to begin / resume.
class MapSelector(UITemplateLoaderExt):

    def __init__(self, control_center, universe):

        UITemplateLoaderExt.__init__(self)


        # Options used on the selection screen
        self.options = []


        # Remember the name of the universe
        self.universe_name = universe.get_name()

        # Keep a list of the maps available in this level selection screen
        self.matches = self.find_matching_map_names(universe)


        # Counter
        index = 1

        # Each map will have a preview on the map selection screen
        for (name, title, status, completion_time, replay_data_path) in self.matches:

            # Let's validate that the universe contains a map by that name
            path = os.path.join( UNIVERSES_PATH, self.universe_name, "maps", "%s.xml" % name )

            # Validate
            if ( os.path.exists(path) ):

                #print "map data:  ", name, status, completion_time, ( type(completion_time) == type("") )
                # Let's create a new option wrapper using the name/title data
                option = MapSelectorOption(
                    name,
                    "%s" % universe.get_map_data(name).get_title()
                )


                # Has the player completed this level?
                if (completion_time > 0):

                    # Configure best completion time
                    option.configure({
                        "best-completion-time": format_framecount_as_time(completion_time)
                    })


                # Configure level index/total data
                option.configure({
                    "level-index": index,
                    "level-count": len(self.matches)
                })


                # Immediately build data for the current level
                universe.build_map_on_layer_by_name(name, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center)


                # Add this preview data to the universe option's list of previews
                preview = option.create_preview(path, universe)


                # Did we find a replay filepath for this level selection option?
                if (replay_data_path):

                    # Save replay filepath as a map param
                    universe.get_map_on_layer_by_name(name, LAYER_FOREGROUND).set_param(
                        "replay-file",
                        os.path.join( UNIVERSES_PATH, universe.get_name(), "replays", replay_data_path )
                    )

                    # Initialize replay data
                    universe.get_map_on_layer_by_name(name, LAYER_FOREGROUND).configure({
                        "replay-file": os.path.join( UNIVERSES_PATH, universe.get_name(), "replays", replay_data_path )
                    })



                # Get new map
                m = universe.get_map_on_layer_by_name(name, LAYER_FOREGROUND)

                # Disable any player entity not named "player1."  **Hack
                for player in m.get_entities_by_type(GENUS_PLAYER):

                    # Validate name
                    if ( player.get_name() != "player1" ):

                        # Disable within this preview
                        player.set_status(STATUS_INACTIVE)

                # Disable all player respawns in preview
                for o in m.get_entities_by_type(GENUS_RESPAWN_PLAYER):

                    # Disable
                    o.set_status(STATUS_INACTIVE)




                # Add the new option to our list of map options
                self.options.append(option)

            # Increment counter
            index += 1


    # Find / validate all maps available on the level selection screen,
    # according to a given Universe object's meta file.
    def find_matching_map_names(self, universe):

        # Track matches
        matches = []


        # Compute metadata path
        metadata_path = os.path.join( UNIVERSES_PATH, universe.name, "meta.xml" )

        # Validate that universe data exists
        if ( os.path.exists(metadata_path) ):

            # The metadata uses the xml format
            f = open(metadata_path, "r")
            xml = f.read()
            f.close()

            # Let's parse the metadata xml
            root = XMLParser().create_node_from_xml(xml).find_node_by_tag("metadata")

            # Validate
            if (root):

                # Look for selection options
                ref_selectable_levels = root.find_node_by_tag("selectable-levels")

                # Validate
                if (ref_selectable_levels):

                    # Loop each child node
                    for ref_selectable_level in ref_selectable_levels.get_nodes_by_tag("selectable-level"):

                        # Check for map data for the given level
                        map_data = universe.get_map_data(
                            ref_selectable_level.innerText
                        )

                        # Validate that we know this map to exist within the given universe
                        if (map_data):

                            # Get the map name from the inner text
                            matches.append(
                                (
                                    ref_selectable_level.innerText,
                                    map_data.get_title(),
                                    "completed!" if ( map_data.is_map_completed() ) else "incomplete",
                                    map_data.completion_time,
                                    ref_selectable_level.get_attribute("replay-file")
                                )
                            )


        # Return the list of matching universe names
        return matches


    # Based on the current set of matching universe names, present the player with the various universes
    # they can choose from.  If we're looking at single-player universes only, we'll show overall completion status.
    # If we're looking at multiplayer only, we'll show how many levels they've completed.  If we're looking at both,
    # we'll show no completion data at all.
    def select(self, tilesheet_sprite, additional_sprites, control_center, universe, active_map_name = None):

        # Prepare a list of options (all of the universes)
        #options = []


        # Track the current cursor selection
        current_option = 0

        # Once we make a selection, we will lock the cursor in place as the window fades.
        cursor_locked = False

        # When we move from one option to another on the vertical axis, we'll instantly move the cursor (for selection logic),
        # but the player will see a gradual scroll.
        current_scroll = 0


        # As we move into the block that renders all of the options, we're going to want a couple of shortcuts to some of the controllers.
        window_controller = control_center.get_window_controller()

        # Handle to the input controller
        input_controller = control_center.get_input_controller()

        # Obviously we'll have text to draw
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()

        # Let's grab the scissor controller as well
        scissor_controller = control_center.get_window_controller().get_scissor_controller()


        # Count how many levels the player has completed, out of the total number of levels...
        (levels_completed, levels_found) = (0, 0)

        # Loop through known options
        for i in range( 0, len(self.options) ):

            # Convenience
            option = self.options[i]


            # Count denominator
            levels_found += 1

            # Complete?
            if ( universe.get_map_data( option.get_name() ).is_map_completed() ):

                # Increment numerator
                levels_completed += 1


            # If we specified this level as the default selection, then let's update the cursor appropriately...
            if ( option.get_name() == active_map_name ):

                # Update cursor
                current_option = i


        # Calculate universe progress for this level set
        progress_percentage = int( (float(levels_completed) / float(levels_found)) * 100.0 )



        # Now let's do one last thing:  I want to load in a Ui widget to serve as the "backdrop" for this
        # selector page.  It's just a header, like on the main menu, except we'll scroll it away as we move
        # from one universe option to another.
        # Fetch the widget dispatcher
        template = self.fetch_xml_template( "mapselector.backdrop", version = "normal" ).add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % int(PAUSE_MENU_Y / 2) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@percent-complete": xml_encode( "%s%%" % progress_percentage )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create the local backdrop widget
        backdrop_widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, None)

        backdrop_widget.set_id("mapselector-backdrop")
        #self.backdrop_widget.focus()


        # Before we begin, let's set the given Universe's camera to the appropriate size for a preview map
        universe.get_camera().set_width(PREVIEW_RADIUS * 2)
        universe.get_camera().set_height(PREVIEW_RADIUS * 2)


        # We need to hack in a quick check for a custom tilesheet for the given universe.
        # Like with UI.gif, we have to do this because the selectors use low-level map drawing functions that skip over the universe's standard tilesheet logic.
        if (universe.custom_tilesheet):

            # Overwrite given tilesheet reference
            tilesheet_sprite = universe.custom_tilesheet


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


            # Ensure that the currently selected option counts as the
            # active map in the given Universe object.
            if ( universe.get_active_map().get_name() != self.options[current_option].get_name() ):

                # Activate the currently highlighted map
                universe.activate_map_on_layer_by_name( self.options[current_option].get_name(), LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center )


            # If we haven't yet made a selection, we will check for cursor control
            if (not cursor_locked):

                # Perhaps the user wants to cancel, go back to the menu without selecting any universe?
                if (
                    (K_ESCAPE in input_controller.get_system_input()["keydown-keycodes"]) or
                    ( input_controller.check_gameplay_action("escape", system_input, [], True) )
                ):

                    # Lock cursor, no point in checking input now...
                    cursor_locked = True

                    # App fade, followed by a "cancel" event on this selector
                    window_controller.fade_out(
                        on_complete = "mapselector:cancel"
                    )

                # Cursor up?
                elif (INPUT_SELECTION_UP in gameplay_input):

                    # If we're on the top row, then let's move to the same column on the last row
                    if (current_option < PER_ROW):

                        # Move to the same column of the final row
                        current_option = (len(self.options) - 1) - (PER_ROW - 1) + (current_option % PER_ROW)

                        # Perhaps the final row doesn't have enough columns.
                        while ( current_option >= len(self.options) ):

                            # We want the last possible column in the last possible row
                            current_option -= 1

                        # Tick sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    # Otherwise, simply move up one row
                    else:

                        # Up one row
                        current_option -= PER_ROW

                        # Wrap around?  This should never happen, but who knows?
                        if (current_option < 0):

                            # Bottom of the list
                            current_option = len(self.options) - 1

                        # Tick sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Cursor down?
                elif (INPUT_SELECTION_DOWN in gameplay_input):

                    # Wrap to top (same column) if we're already on the final row
                    if ( int(current_option / PER_ROW) == ( (len(self.options) / PER_ROW) - 1 ) ):

                        # Move up to the top row
                        while (current_option >= PER_ROW):

                            # Skip, skip, skip, this is clever coding!
                            current_option -= PER_ROW

                        # Tick sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)


                    # If we're not already on the final option, try to move down
                    else:

                        # Move down one row
                        current_option += PER_ROW

                        # Let's just play it safe.  We should have a row to move to, but who knows?
                        if ( current_option >= len(self.options) ):

                            # To the top!
                            current_option = 0

                        # Tick sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Cursor left?
                elif (INPUT_SELECTION_LEFT in gameplay_input):

                    # If we're on the left-most column, skip over to the right side
                    if ( (current_option % PER_ROW) == 0 ):

                        # Move ahead by row size
                        current_option += (PER_ROW - 1)

                    # Otherwise, move left by one column
                    else:

                        # One step
                        current_option -= 1


                    # Don't step out of bounds on the last row
                    if ( current_option >= len(self.options) ):

                        # Clamp
                        current_option = len(self.options) - 1


                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Cursor right?
                elif (INPUT_SELECTION_RIGHT in gameplay_input):

                    # If we're on the right-most column, we'll wrap back to the left
                    if ( (current_option == len(self.options) - 1) or ((current_option % PER_ROW) == (PER_ROW - 1)) ):

                        # Move to the first option in the current row
                        current_option = int(current_option / PER_ROW) * PER_ROW

                    # Otherwise, move ahead by one column
                    else:

                        # Step by one
                        current_option += 1


                    # Stay in bounds
                    if ( current_option >= len(self.options) ):

                        # Clamp
                        current_option = len(self.options) - 1


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
                    current_option = ( len(self.options) - 1 )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Page up?
                elif (INPUT_SELECTION_PAGEUP in gameplay_input):

                    # Let's move up by 2 rows, that's about how many fit on a page
                    current_option -= (2 * PER_ROW)

                    # Don't wrap
                    if (current_option < 0):

                        # Clamp
                        current_option = 0

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Page down?
                elif (INPUT_SELECTION_PAGEDOWN in gameplay_input):

                    # Go down by 2 rows, that's about how many fit on a page
                    current_option += (2 * PER_ROW)

                    # Don't wrap
                    if ( current_option >= len(self.options) ):

                        # Clamp
                        current_option = ( len(self.options) - 1 )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                # Select current universe option?
                elif (INPUT_SELECTION_ACTIVATE in gameplay_input):

                    # Fade the app window, raising a special-case escape event when done.
                    window_controller.fade_out(
                        on_complete = "mapselector:escape"
                    )

                    # Lock future cursor movement as we fade out
                    cursor_locked = True

                    # Select sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_SELECT)


            # The scroll should always target the current option
            scroll_target = ( int(current_option / PER_ROW) * OPTION_HEIGHT)


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


            # Lock all input (we don't want the player's key movements affecting the GIFs!)
            control_center.get_input_controller().lock_all_input()

            # Process the given Universe object
            universe.process_game_logic(control_center)

            # Unlock input
            control_center.get_input_controller().unlock_all_input()


            # Try to get the active map
            m = universe.get_active_map()

            # Validate
            if (m):

                # Fetch player 1 entity
                player = m.get_entity_by_name("player1")

                # Process map replay data using this GIF's Universe object
                m.process_replay_data(control_center, universe)


                # Check map for reload flag
                if (m.requires_reload):

                    # Before disposing of the Map object, let's recall the path to the replay data
                    replay_data_path = m.get_param("replay-file")

                    # Remember map name for a moment
                    name = universe.remove_map_on_layer_by_name( m.name, LAYER_FOREGROUND ).name # .remove_... returns the removed map, we'll borrow its name


                    # Immediately send a fresh build map request, thus "reloading" the map
                    universe.build_map_on_layer_by_name(name, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center)

                    # Activate the map
                    universe.activate_map_on_layer_by_name(name, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center)


                    # Did the active map have a replay filepath?
                    if (replay_data_path):

                        # We also must again set the param for continuous looping
                        universe.get_active_map().set_param(
                            "replay-file",
                            replay_data_path
                        )

                        # Initialize replay data on the rebuilt Map object
                        universe.get_active_map().configure({
                            "replay-file": replay_data_path
                        })



            # Loop through each available option
            for i in range( 0, len(self.options) ):

                #print "%d - %s" % (i, self.options[i].name)
                #text_renderer.render_with_wrap( "%d - %s" % (i, self.options[i].name), 5, 5 + (i * text_renderer.font_height), (225, 225, 25))

                # Process the option (alpha / preview logic)
                self.options[i].process( (i == current_option), control_center, universe )

                (sx, sy) = (
                    PAUSE_MENU_X + ((i % PER_ROW) * (OPTION_WIDTH + COLUMN_PADDING)) + PREVIEW_PADDING,
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + ( int(i / PER_ROW) * OPTION_HEIGHT ) - (current_scroll)
                )

                scissor_controller.push( (sx, sy, 2 * PREVIEW_RADIUS, 2 * PREVIEW_RADIUS) )

                # Fetch the Map object for this option
                m = universe.get_map_on_layer_by_name(
                    self.options[i].get_name(),
                    LAYER_FOREGROUND
                )

                # Map dimensions, in pixels
                (width, height) = (
                    m.get_width_in_pixels(),
                    m.get_height_in_pixels()
                )


                # Default to centering on the center of the map
                (cx, cy) = (
                    int(width / 2),
                    int(height / 2)
                )

                # We prefer, though, to center on the player entity.
                player = m.get_entity_by_name("player1")

                # Validate
                if (player):

                    # We'll center on the player's center
                    (cx, cy) = (
                        player.get_x() + int(TILE_WIDTH / 2),
                        player.get_y() + int(TILE_HEIGHT / 2)
                    )


                # Calculate where we should render the map
                (rx, ry) = (
                    sx - cx + int(PREVIEW_RADIUS),
                    sy - cy + int(PREVIEW_RADIUS)
                )


                # Let's constantly center on what the player in the replay is doing
                universe.center_camera_on_map(
                    universe.get_map_on_layer_by_name(
                        self.options[i].get_name(),
                        LAYER_FOREGROUND
                    )
                )


                # Don't render offscreen maps (pointless and ruins performance)
                if ( (ry + height >= 0) and (ry <= SCREEN_HEIGHT) ):

                    # Render the map associated with this option
                    universe.draw_map_on_layer_with_explicit_offset(
                        self.options[i].get_name(), # Map name
                        LAYER_FOREGROUND,
                        rx,
                        ry,
                        tilesheet_sprite,
                        additional_sprites,
                        MODE_GAME,
                        control_center
                    )


                scissor_controller.pop()


                """ (Greyscale isn't working for some reason; maybe I'll try it again another time...)
                # If this is not the selected option, render it in greyscale...
                if (i != current_option):

                    # Greyscale effect
                    window_controller.get_gfx_controller().apply_greyscale_effect_to_screen(sx, sy, 2 * PREVIEW_RADIUS, 2 * PREVIEW_RADIUS)
                """


                # Add a "spotlight" effect
                window_controller.get_geometry_controller().draw_exclusive_circle_with_radial_gradient(sx + PREVIEW_RADIUS, sy + PREVIEW_RADIUS, PREVIEW_RADIUS, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


                #map_name, layer, sx, sy, tilesheet_sprite, additional_sprites, game_mode, control_center, max_x = SCREEN_WIDTH, max_y = SCREEN_HEIGHT, scale = None, gl_color = (1, 1, 1, 1)):


            # Debug
            #window_controller.get_gfx_controller().apply_radial_greyscale_effect_to_screen(0, 0, 640, 480, 1.0, 235)

            for i in range( 0, len(self.options) ):

                (sx, sy) = (
                    PAUSE_MENU_X + ((i % PER_ROW) * (OPTION_WIDTH + COLUMN_PADDING)) + PREVIEW_RADIUS + PREVIEW_PADDING,
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + ( int(i / PER_ROW) * OPTION_HEIGHT ) - (current_scroll)
                )

                indent = 0
                if ( i == current_option ):

                    indent = 10

                # If this is the current option (if and only if), then we shall render the title of the universe above the glow area.
                # We'll render it independent of scrolling action (just like the glow area), perhaps as an indicator that they can hit enter immediately??
                if (i == current_option):

                    # Yeah, I'm indenting by the font height.  I just want a little margin...
                    text_renderer.render_with_wrap( "\"%s\"" % self.options[i].get_title(), PAUSE_MENU_X + ((i % PER_ROW) * (OPTION_WIDTH + COLUMN_PADDING)) + text_renderer.font_height, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2) - int(1.1 * text_renderer.font_height), (225, 225, 225) )
                    #self.options[i].draw_labels( indent + sx, sy + PREVIEW_RADIUS, text_renderer, window_controller, active = (i == current_option) )


                (sx, sy) = (
                    PAUSE_MENU_X + ((i % PER_ROW) * (OPTION_WIDTH + COLUMN_PADDING)) + text_renderer.font_height,#(2 * PREVIEW_RADIUS) + (2 * PREVIEW_PADDING),
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + ( int(i / PER_ROW) * OPTION_HEIGHT ) - (current_scroll)
                )

                self.options[i].draw_singleplayer_completion_data( indent + sx, sy, PAUSE_MENU_WIDTH - ((2 * PREVIEW_RADIUS) + (2 * PREVIEW_PADDING)), (2 * PREVIEW_RADIUS), text_renderer, active = (i == current_option) )


            # Render position for the highlight gradient stuff
            (rx, ry) = (
                ((current_option % PER_ROW) * (OPTION_WIDTH + COLUMN_PADDING)),
                0 # Unused, currently...
            )

            #text_renderer.render_with_wrap("Try to collect all of the gold in this story while avoiding all of the bad guys!", int(0.75 * SCREEN_WIDTH), int(SCREEN_HEIGHT / 2), (175, 175, 175), max_width = int(0.5 * SCREEN_WIDTH), align = "center")
            # ...
            window_controller.get_geometry_controller().draw_rect(rx + PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), OPTION_WIDTH, OPTION_HEIGHT, (225, 225, 225, 0.075))

            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( rx + PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), int(0.25 * OPTION_WIDTH), 2, (225, 225, 225, 0.05), (225, 225, 225, 0.25) )
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( rx + PAUSE_MENU_X + int(0.25 * OPTION_WIDTH), int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), int(0.75 * OPTION_WIDTH), 2, (225, 225, 225, 0.25), (225, 225, 225, 0.05) )

            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( rx + PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) + int(OPTION_HEIGHT / 2) - 2, int(0.25 * OPTION_WIDTH), 2, (225, 225, 225, 0.05), (225, 225, 225, 0.25) )
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( rx + PAUSE_MENU_X + int(0.25 * OPTION_WIDTH), int(SCREEN_HEIGHT / 2) + int(OPTION_HEIGHT / 2) - 2, int(0.75 * OPTION_WIDTH), 2, (225, 225, 225, 0.25), (225, 225, 225, 0.05) )


            # Render "tapering" effect
            #window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, 0, SCREEN_WIDTH, TAPER_AREA_SIZE, (0, 0, 0, 1.0), (0, 0, 0, 0.0))
            window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, (SCREEN_HEIGHT - TAPER_AREA_SIZE), SCREEN_WIDTH, TAPER_AREA_SIZE, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


            # Process window controller
            results = window_controller.process(control_center, None) # (?) no universe? ??? #some_universe) some_universe? ? ?

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


                # Special case - exit map selector
                if ( action == "mapselector:escape" ):

                    # Return the name of the map selection we made
                    return self.options[current_option].get_name()

                # Special case - cancel map selector
                elif ( action == "mapselector:cancel" ):

                    # Return nothing, indicating that we did not select any universe (i.e. just go back to the menu)
                    return None

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
