import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue, EventQueueIter

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, logn, xml_encode, xml_decode, sort_files_by_date, get_file_modified_time, format_timedelta, translate_rgb_to_string, safe_round

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, CAMERA_SPEED, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_ACTIVATE, PAUSE_MENU_PROMPT_WIDTH, PAUSE_MENU_PROMPT_CONTENT_WIDTH, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, SKILLS_BY_CATEGORY, CATEGORIES_BY_SKILL, SKILL_OPPOSITES, SKILL_ICON_INDICES, DATE_WIDTH, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, MAX_QUICKSAVE_SLOTS, MAX_AUTOSAVE_SLOTS, PAUSE_MENU_PRIZE_AD_HEIGHT, OVERWORLD_GAME_OVER_MENU_WIDTH, DEFAULT_PLAYER_COLORS, WORLDMAP_VIEW_LABELS, CATEGORY_LABELS, MAX_SKILL_SLOTS, LAYER_FOREGROUND, LAYER_BACKGROUND, SPLASH_MODE_GREYSCALE_ANIMATED, REPUTATION_READY
from code.constants.paths import UNIVERSES_PATH

from code.constants.network import NET_STATUS_SERVER, NET_STATUS_CLIENT

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY
from code.constants.newsfeeder import *

from pygame.locals import K_ESCAPE, K_RETURN

class PauseMenu(Menu):

    def __init__(self):#, x, y, w, h, text_renderer, save_controller, network_controller, universe, session, widget_dispatcher, ref_skilltrees):

        Menu.__init__(self)#, x, y, w, h, universe, session)


        # Define a grid menu for each tab page
        self.grid_menus = {}

        # We'll load in skillset definitions at runtime; we'll key them by category (e.g. "movement" or "control").
        self.skillsets = {}


        # Keep a handle to the ref_skilltrees node
        self.ref_skilltrees = None#ref_skilltrees


        # Track if we are building the pause menu for the first time
        self.first_build = True

        # Add a command to the queue to build the widget
        self.fire_event("build")


        """ Debug param """
        self.lifespan = 0


    """ Begin DEBUG """
    # I want a quick escape from the main menu.  Maybe I make this permanent later...
    def additional_processing(self, control_center, universe, debug = False):#user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, debug = False):

        # Local events
        results = EventQueue()

        # Hack to avoid responding to same keypress that summoned menu
        if (self.lifespan > 1):

            # Fetch touched keys to use as raw keyboard input
            touched_keys = control_center.get_input_controller().get_touched_keys()

            # Hitting ESC or "enter" should kill the pause menu
            if (K_ESCAPE in touched_keys):

                # Fire kill event
                self.fire_event("resume-game")

        # Track lifespan
        self.lifespan += 1

        # Return events
        return results
    """ End DEBUG """


    # Create a tab by a given name (based on the navbar selection)
    def create_tab(self, tab_name, control_center, universe):#widget_dispatcher, universe, session):

        a = time.time()

        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        log( tab_name )

        # Fetch template data for the given tab
        template = self.fetch_xml_template(tab_name).add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@box-height": xml_encode( "%d" % 140 ) # hard-coded, used for uniformity of boxes despite varying content heights
        })

        # Compile template
        root = template.compile_node_by_id("tab")



        # If we're looking at the skills tab, we're going to need to update the various
        # readouts to reflect the state of each skill (i.e. upgrade available?  locked?  etc.)
        if (tab_name == "gamemenu.tabs.skills"):

            # Grab the current player character level
            character_level = int( universe.get_session_variable("core.player1.level").get_value() )

            # Get the skill-stats object, we'll need it...
            skill_stats = universe.get_skill_stats()


            # Zebra tracking
            zebra = False

            # Loop through each possible skill category
            for category in SKILLS_BY_CATEGORY:

                # Which template version will we use?
                version = "normal"

                # Zebrafy?
                if (zebra):

                    version = "%s:zebra" % version


                # Before retrieving the template and parameterizing, let's calculate the parameters we'll use.
                # Start with some generic defaults...
                params = {
                    "@status": xml_encode( "No action available" ),
                    "@level": xml_encode( "[color=dim]n/a[/color]" ),
                    "@upgrade-msg": xml_encode( "" ),
                    "@disabled": xml_encode( "0" ),
                    "@category-name": xml_encode( category ),
                    "@skill-title": xml_encode( "" ),
                    "@skill-icon-index": xml_encode( "13" ),
                    "@category-title": xml_encode( CATEGORY_LABELS[category] ),
                    "@box-height": xml_encode( "%d" % 140 ) # hard-coded, used for uniformity of boxes despite varying content heights
                }


                # We may add certain notes to the widget (e.g. "Level: 1," "Upgrade Ready!," "Choose a skill...")
                notes = []


                # Based on the min-character-level of the 2 skills in the category, we'll determine
                # the minimum character level for the category.
                min_character_level = None

                # Has the player unlocked either skill?
                unlocked_category = False

                # If so, then we'll want to track which skill they chose...
                selected_skill = None

                # And if so, we'll want to also track whether or not they have a "next" upgrade available (e.g. Level 1 upgrades to Level 2)
                next_upgrade_available = 0

                # Has the player fully upgraded the skill they chose in this category?
                fully_upgraded = False


                # For the initial "Select [a] or [b]," I'll need to keep a reference to the two skills' names...
                skill_options = []


                # Check both skills in this category...
                for skill in SKILLS_BY_CATEGORY[category]:

                    # Append this skill label to the "options" list in case we render a "Select [a] or [b]" string
                    skill_options.append("[color=skill]%s[/color]" % SKILL_LABELS[skill])


                    # Irregardless of which skill the player has chosen, we'll use the same icon, so let's just set it twice
                    params["@skill-icon-index"] = xml_encode( "%d" % SKILL_ICON_INDICES[skill] )


                    # What level of this skill does the player have?  (Any?)
                    player_skill_level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )

                    # If the player has the skill, update the #LEVEL label
                    if (player_skill_level > 0):

                        # Label
                        params["@level"] = xml_encode( "[color=special]%d[/color]" % player_skill_level )
                        params["@category-title"] = xml_encode( SKILL_LABELS[skill] )

                        # Add a note describing the skill level
                        notes.append( "Level:  [color=special]%d[/color]" % player_skill_level )

                        # We've unlocked this category and selected this very skill...
                        unlocked_category = True
                        selected_skill = skill


                    # Check each possible level of this skill to determine various data
                    for level in (1, 2, 3):

                        # Get stats for this skill/level
                        stats = skill_stats.get_skill_stats_by_level(skill, level)

                        # Validate
                        if (stats):

                            # If we haven't defined min-character-level yet, then this first found skill will set that floor
                            if (min_character_level == None):

                                min_character_level = stats.get_min_character_level()

                            # If we've already unlocked this category (and selected this skill), this level might be an upgrade...
                            if (player_skill_level > 0):

                                # If this skill level is higher than the player's current version, are they qualified to unlock it?
                                if ( (character_level >= stats.get_min_character_level()) and (level > player_skill_level) ):

                                    #print level, ">", player_skill_level, "(%s)" % skill

                                    # If they're eligible for level 3 but only have level 1, we want to start by advertising Level 2 only...
                                    if (not next_upgrade_available):

                                        next_upgrade_available = level


                # If we haven't unlocked anything...
                if (not unlocked_category):

                    # Still locked
                    if (character_level < min_character_level):

                        # We can't access this category yet...
                        params["@disabled"] = xml_encode( "1" )

                        # Let the player know when they can access this category
                        #params["@status"] = xml_encode( "Unlocks at [color=locked]Character Level %d[/color]" % min_character_level )
                        notes.append( "Unlocks at [color=special]Character Level %d[/color]" % min_character_level )

                    # Select [a] or [b]
                    else:

                        # We can access this category to select a skill
                        params["@disabled"] = xml_encode( "0" )

                        # Display selection options
                        #params["@status"] = xml_encode( "Select [color=skill]%s[/color] or [color=skill]%s[/color]" % (skill_options[0], skill_options[1]) )
                        notes.append( "Select [color=special]%s[/color] or [color=special]%s[/color]" % (skill_options[0], skill_options[1]) )


                # We might have upgrades available?
                else:

                    # We can access this category now, either to unlock a skill or to upgrade a skill
                    params["@disabled"] = xml_encode( "0" )


                    # All done
                    if (fully_upgraded):

                        params["@status"] = xml_encode( "Fully upgraded!" )

                        notes.append( "Fully upgraded!" )

                    # Not all done.  Have we at least chosen a skill in this category?
                    elif (selected_skill):

                        # Display selected skill
                        params["@status"] = xml_encode( "[color=skill]%s[/color]" % SKILL_LABELS[selected_skill] )

                        # Any upgrade available?
                        if (next_upgrade_available > 0):

                            params["@upgrade-msg"] = xml_encode( "[color=skill]Level %d[/color] Unlocked" % next_upgrade_available )

                            notes.append( "[color=special]Level %d[/color] unlocked!" % next_upgrade_available )

                    # Well, this should never happen, but who knows?
                    else:
                        params["@status"] = xml_encode( "No action available" )


                # Now we can retrieve and parameterize the template
                # Fetch the insert template
                template = self.fetch_xml_template( "gamemenu.tabs.skills.insert", version = version ).add_parameters(
                    params
                )

                # Compile template
                node = template.compile_node_by_id("insert")


                # Process any details that apply to this category (unlock messages, upgrade, level, etc.)
                for note in notes:

                    # Fetch the detail template
                    template = self.fetch_xml_template( "gamemenu.tabs.skills.insert.detail", version = "normal" ).add_parameters({
                        "@text": xml_encode( note )
                    })

                    # Compile the detail node
                    detail_node = template.compile_node_by_id("detail")

                    # Add it to the overall skill/category insert node
                    node.find_node_by_id("details").add_node(detail_node)



                # Add the new node to the skills group
                root.find_node_by_id("ext.skills").add_node(node)


                # Paint stripes on our beautiful zebra friend
                zebra = (not zebra)

                #for key in labels:
                #    temp_xml = temp_xml.replace("#%s" % key.upper(), labels[key])


                #f = open( os.path.join("debug", "debug.grid.xml"), "a" )
                #f.write(temp_xml + "\n")
                #f.close()

            #print ref_grid.compile_xml_string()

            #print 5/0


        logn( "pause-menu", "Compiled markup in %s seconds." % (time.time() - a) )
        a = time.time()

        # Create the widget we'll use for this tab, then configure...
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        logn( "pause-menu", "Converted to widget in %s seconds." % (time.time() - a) )

        # Return new tab
        return widget


    def handle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        action = event.get_action()

        log2( action + "\n", event.get_params() )


        # Set up the initial page
        if ( action == "build" ):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        elif ( action == "navbar-wrap-down"):

            results.append(
                self.handle_navbar_wrap_down_event(event, control_center, universe)
            )


        elif ( action == "navbar-change" ):

            results.append(
                self.handle_navbar_change_event(event, control_center, universe)
            )


        # Current tab has a cursor wrap
        elif ( action == "tab-wrap-down" ):

            results.append(
                self.handle_tab_wrap_down_event(event, control_center, universe)
            )


        # Current tab loses its cursor somehow
        elif ( action == "tab-abort" ):

            results.append(
                self.handle_tab_abort_event(event, control_center, universe)
            )


        # Show a new menu page with the skills in a given tree
        elif ( action == "show:skills.tree" ):

            results.append(
                self.handle_show_skill_tree_event(event, control_center, universe)
            )


        # "Descend" into a given skill tree option (e.g. select either Earth Mover or Jackhammer),
        # shifting the skill tree to the top, hiding everything unrelated to the selected skill,
        # and introducing a new page with additional details and the commit upgrade button.
        elif ( action == "show:skills.tree.insert.options" ):

            results.append(
                self.handle_show_skill_tree_insert_options_event(event, control_center, universe)
            )


        # Confirm that the player definitely wants to unlock/upgrade a given skill
        elif ( action == "show:skills.tree.insert.options.upgrade.confirm" ):#" ):

            results.append(
                self.handle_show_skill_tree_insert_options_upgrade_confirm_event(event, control_center, universe)
            )


        # Follow through with a given skill upgrade
        elif ( action == "commit:skills.tree.insert.options.upgrade" ):

            results.append(
                self.handle_commit_skill_tree_insert_options_upgrade_event(event, control_center, universe)
            )


            """
            # Define params to trigger a receipt
            (event_type, event_params) = (
                "upgrade-skill:receipt",
                {
                    "-skill-name": params["-skill-name"],
                    "-level": params["-level"]
                }
            )

            # Lastly, dismiss the popup that asked for confirmation, and follow it up with a receipt (i.e. "You upgraded!")
            self.overlay_collection[-1].dismiss(
                lambda s = self, event_type = event_type, event_params = event_params: s.fire_event_with_params(event_type, event_params)
            )
            """


        # Abandon the "skill options" page (e.g. upgrade or cancel) and return to the directory,
        # undoing all of the slide offset logic we applied when we created the options page.
        elif ( action == "hide:skill.tree.insert.options" ):

            results.append(
                self.handle_hide_skill_tree_insert_options_event(event, control_center, universe)
            )


        # Hide the "final confirmation" options for a skill upgrade
        elif ( action == "hide:skill.tree.insert.options.upgrade.confirm" ):

            results.append(
                self.handle_hide_skill_tree_insert_options_upgrade_confirm_event(event, control_center, universe)
            )





        # Allow player to view and edit their equipped skills
        elif ( action == "show:game.skills" ):

            results.append(
                self.handle_show_game_skills_event(event, control_center, universe)
            )


        # Show a list of all of the skills, allowing the user to pick one to assign to a given skill slot
        elif ( action == "show:game.skills.equipped.insert.options" ):

            results.append(
                self.handle_show_game_skills_equipped_insert_options_event(event, control_center, universe)
            )


        # Hide the list of skills the user chooses from for a given skill slot
        elif ( action == "hide:game.skills.equipped.insert.options" ):

            results.append(
                self.handle_hide_game_skills_equipped_insert_options_event(event, control_center, universe)
            )


        elif ( action == "show:game.skills.all.insert.options" ):

            results.append(
                self.handle_show_game_skills_all_insert_options_event(event, control_center, universe)
            )


        # Hide the options for a skill in the list of acquired skills
        elif ( action == "hide:game.skills.all.insert.options" ):

            results.append(
                self.handle_hide_game_skills_all_insert_options_event(event, control_center, universe)
            )


        # Assign the selected skill to the selected slot...
        elif ( action == "commit:game.skills.assign" ):

            results.append(
                self.handle_commit_game_skills_assign_event(event, control_center, universe)
            )


        # Save game listing (new save option, all quicksaves, manual saves)
        elif ( action == "show:game.save" ):

            results.append(
                self.handle_show_game_save_event(event, control_center, universe)
            )


        # Transition to the save game keyboard from a fading page
        elif ( action == "transition:save-game-keyboard" ):

            results.append(
                self.handle_transition_save_game_keyboard_event(event, control_center, universe)
            )


        # Prompt for the name of a new save...
        elif ( action == "show:game.save.keyboard" ):

            results.append(
                self.handle_show_game_save_keyboard_event(event, control_center, universe)
            )


        # Discard the save game keyboard
        elif ( action == "hide:game.save.keyboard" ):

            results.append(
                self.handle_hide_game_save_keyboard_event(event, control_center, universe)
            )


        # Handle the "enter" command from the save game keyboard
        elif ( action == "submit:game.save.keyboard" ):

            results.append(
                self.handle_submit_game_save_keyboard_event(event, control_center, universe)
            )


        # Get confirmation that a user truly wants to overwrite a quicksave or manual save...
        elif ( action == "show:game.save.overwrite.confirm" ):

            results.append(
                self.handle_show_game_save_overwrite_confirm_event(event, control_center, universe)
            )


        # When the user confirms they want to overwrite a save, we should dismiss the yes/no overlay
        # and display the keyboard once the confirm prompt disappears, if necessary.
        elif ( action == "confirm:game.save.overwrite" ):

            results.append(
                self.handle_confirm_game_save_overwrite_event(event, control_center, universe)
            )


        # Commit a save job
        elif ( action == "commit:game.save.save" ):

            results.append(
                self.handle_commit_game_save_save_event(event, control_center, universe)
            )


        # Load game selection
        elif ( action == "show:game.load" ):

            results.append(
                self.handle_show_game_load_event(event, control_center, universe)
            )


        # Confirm load game ("are you sure?")
        elif ( action == "show:game.load.confirm" ):

            results.append(
                self.handle_show_game_load_confirm_event(event, control_center, universe)
            )


        # Process some dialog stuff...
        elif ( action == "commit:game.load.load" ):

            results.append(
                self.handle_commit_game_load_load_event(event, control_center, universe)
            )


        # Honest-to-goodness, let's load a game already!
        elif ( action == "fwd.transparent:game.load.load" ):

            results.append(
                self.handle_transparent_game_load_load_event(event, control_center, universe)
            )


        # World map view
        elif ( action == "show:game.worldmap" ):

            results.append(
                self.handle_show_game_worldmap_event(event, control_center, universe)
            )


        # Step into worldmap options rowmenu
        elif ( action == "show:game.worldmap:step-in-beginning" ):

            results.append(
                self.handle_show_game_worldmap_step_in_event(event, control_center, universe, "beginning")
            )


        # Step into worldmap options rowmenu
        elif ( action == "show:game.worldmap:step-in-end" ):

            results.append(
                self.handle_show_game_worldmap_step_in_event(event, control_center, universe, "end")
            )


        # Step out of worldmap options rowmenu
        elif ( action == "show:game.worldmap:step-out" ):

            results.append(
                self.handle_show_game_worldmap_step_out_event(event, control_center, universe)
            )


        # Show a dialog that lists possible worldmap view types
        elif ( action == "show:game.worldmap.views" ):

            results.append(
                self.handle_show_game_worldmap_views_event(event, control_center, universe)
            )


        # Set the type of world map (gold map, puzzle map, etc.)
        elif ( action == "commit:game.worldmap.views.set" ):

            results.append(
                self.handle_commit_game_worldmap_views_set_event(event, control_center, universe)
            )


        # Interact with the worldmap (pan, zoom, etc.)
        elif ( action == "commit:game.worldmap.use" ):

            results.append(
                self.handle_commit_game_worldmap_use_event(event, control_center, universe)
            )


        # Show the "are you sure you want to travel?" dialog
        elif ( action == "show:game.worldmap.travel.confirm" ):

            results.append(
                self.handle_show_game_worldmap_travel_confirm_event(event, control_center, universe)
            )


        # Travel to a given town
        elif ( action == "commit:game.worldmap.travel" ):

            results.append(
                self.handle_commit_game_worldmap_travel_event(event, control_center, universe)
            )


        # (Fwd) Finish a map travel command, after a screen fade
        elif ( action == "fwd.finish:game.worldmap.travel" ):

            results.append(
                self.handle_fwd_finish_game_worldmap_travel_event(event, control_center, universe)
            )


        # Worldmap yields focus back to the directory
        elif ( action == "commit:game.worldmap.yield" ):

            results.append(
                self.handle_commit_game_worldmap_yield_event(event, control_center, universe)
            )


        # Show the "my reputation" menu screen
        elif ( action == "show:inventories.reputation" ):

            results.append(
                self.handle_show_inventories_reputation_event(event, control_center, universe)
            )


        # Scroll up the non-selectable "my reputation" text
        elif ( action == "reputation:scroll-up" ):

            results.append(
                self.handle_reputation_scroll_up_event(event, control_center, universe)
            )


        # Scroll down the non-selectable "my reputation" text
        elif ( action == "reputation:scroll-down" ):

            results.append(
                self.handle_reputation_scroll_down_event(event, control_center, universe)
            )


        # Show the inventory management menu screen
        elif ( action == "show:inventories.inventory" ):

            results.append(
                self.handle_show_inventories_inventory_event(event, control_center, universe)
            )


        # Show user options for an equipped item (e.g. Unequip, Cancel, etc.)
        elif ( action == "show:inventories.inventory.equipped.options" ):

            results.append(
                self.handle_show_inventories_inventory_equipped_options_event(event, control_center, universe)
            )


        # Slide the options offscreen, direct inventory to return to default slide position
        elif ( action == "hide:inventories.inventory.equipped.options" ):

            results.append(
                self.handle_hide_inventories_inventory_equipped_options_event(event, control_center, universe)
            )


        elif ( action == "show:inventories.inventory.all.options" ):

            results.append(
                self.handle_show_inventories_inventory_all_options_event(event, control_center, universe)
            )


        # Slide the options offscreen, direct inventory to return to default slide position
        elif ( action == "hide:inventories.inventory.all.options" ):

            results.append(
                self.handle_hide_inventories_inventory_all_options_event(event, control_center, universe)
            )


        # Show the "confirm upgrade" alert
        elif ( action == "show:inventories.inventory.item.upgrade.confirm" ):

            results.append(
                self.handle_show_inventories_inventory_item_upgrade_confirm_event(event, control_center, universe)
            )


        # Prompt to replace an existing item with a different item
        elif ( action == "show:inventories.inventory.item.replace.options" ):

            results.append(
                self.handle_show_inventories_inventory_item_replace_options_event(event, control_center, universe)
            )


        # Hide the "replace item" page
        elif ( action == "hide:inventories.inventory.item.replace.options" ):

            results.append(
                self.handle_hide_inventories_inventory_item_replace_options_event(event, control_center, universe)
            )


        # Commit an item replace
        elif ( action == "game:replace-item" ):

            results.append(
                self.handle_game_replace_item_event(event, control_center, universe)
            )


        # Equip an item
        elif ( action == "game:equip-item" ):

            results.append(
                self.handle_game_equip_item_event(event, control_center, universe)
            )


        # Unequip an item
        elif ( action == "game:unequip-item" ):

            results.append(
                self.handle_game_unequip_item_event(event, control_center, universe)
            )


        # Upgrade an item (final commit)
        elif ( action == "game:upgrade-item" ):

            results.append(
                self.handle_game_upgrade_item_event(event, control_center, universe)
            )


        # Show the active quests screen
        elif ( action == "show:quests.active" ):

            results.append(
                self.handle_show_quests_active_event(event, control_center, universe)
            )


        # Show the finished quests screen
        elif ( action == "show:quests.finished" ):

            results.append(
                self.handle_show_quests_finished_event(event, control_center, universe)
            )


        # Show all updates for a given quest (active or otherwise, multipurpose
        elif ( action == "show:quest.updates" ):

            results.append(
                self.handle_show_quest_updates_event(event, control_center, universe)
            )


        # Show in-game controls editing (this shows either keyboard or gamepad, according to most recently used device)
        elif ( action == "show:options.controls" ):

            results.append(
                self.handle_show_options_controls_event(event, control_center, universe)
            )


        # Prompt for keyboard control customization for a given input action
        elif ( action == "show:edit-keyboard-control" ):

            results.append(
                self.handle_show_edit_keyboard_control_event(event, control_center, universe)
            )


        # Update a given keyboard control, set to a given keycode
        elif ( action == "game:update-keyboard-control" ):

            results.append(
                self.handle_game_update_keyboard_control_event(event, control_center, universe)
            )


        # Show the "are you sure" dialog
        elif ( action == "show:reset-keyboard-controls" ):

            results.append(
                self.handle_show_reset_keyboard_controls_event(event, control_center, universe)
            )


        # Commit a keyboard controls reset
        elif ( action == "game:reset-keyboard-controls" ):

            results.append(
                self.handle_game_reset_keyboard_controls_event(event, control_center, universe)
            )


        # Prompt for gamepad control customization for a given input action
        elif ( action == "show:edit-gamepad-control" ):

            results.append(
                self.handle_show_edit_gamepad_control_event(event, control_center, universe)
            )


        # Update a given gamepad control, set to a given device input type / index / whatever
        elif ( action == "game:update-gamepad-control" ):

            results.append(
                self.handle_game_update_gamepad_control_event(event, control_center, universe)
            )


        # The "update gamepad control" dialog has a keyboard listener that will only care about the ESC key...
        elif ( action == "abort:edit-gamepad-control" ):

            results.append(
                self.handle_abort_edit_gamepad_control_event(event, control_center, universe)
            )


        elif ( action == "show:reset-gamepad-controls" ):

            results.append(
                self.handle_show_reset_gamepad_controls_event(event, control_center, universe)
            )


        elif ( action == "game:reset-gamepad-controls" ):

            results.append(
                self.handle_game_reset_gamepad_controls_event(event, control_center, universe)
            )


        # Save controls
        elif ( action == "game:save-controls" ):

            results.append(
                self.handle_game_save_controls_event(event, control_center, universe)
            )


        # Transaction history
        elif ( action == "show:options.transactions" ):

            results.append(
                self.handle_show_options_transactions_event(event, control_center, universe)
            )


        # Show the achievements menu
        elif ( action == "show:options.achievements" ):

            results.append(
                self.handle_show_options_achievements_event(event, control_center, universe)
            )


        # Show the gameplay statistics menu
        elif ( action == "show:options.statistics" ):

            results.append(
                self.handle_show_options_statistics_event(event, control_center, universe)
            )


        # Return to previous page without animation
        elif ( action == "hide" ):

            results.append(
                self.handle_hide_event(event, control_center, universe)
            )


        # Dismiss a widget page, returning to the previous page on completion...
        elif ( action in ("root", "back") ):

            results.append(
                self.handle_back_event(event, control_center, universe)
            )


        # Commit the "one page back" event
        elif ( action == "transparent:back" ):

            results.append(
                self.handle_transparent_back_event(event, control_center, universe)
            )


        # Complete a "slide back"
        elif ( action == "transparent:slide-back" ):

            results.append(
                self.handle_transparent_slide_back_event(event, control_center, universe)
            )


        # Unused?
        elif ( action == "previous-page" ):

            # Let's just call this one directly
            self.page_back(1)


        # Dismiss pause menu
        elif ( action == "resume-game" ):

            results.append(
                self.handle_resume_game_event(event, control_center, universe)
            )


        # Return to main menu
        elif ( action == "leave-game" ):

            results.append(
                self.handle_leave_game_event(event, control_center, universe)
            )


        # (Forwarded) Finish "leave game" and return to main menu
        elif ( action == "fwd.finish:leave-game" ):

            results.append(
                self.handle_fwd_finish_leave_game_event(event, control_center, universe)
            )


        # Restore the universe to active game state, set this very PauseMenu to inactive
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    def quickview_active_quest(self, quest_name, universe, text_renderer):

        # Let's "activate" the pause menu first...
        self.activate()

        # Next, set the hmenu navbar to "Inventories"
        self.get_overlay_item_by_id("root").get_widget().get_item_at_index(0).get_widget().set_value_by_name("inventories")


        # Now we need to fire some events (well, 1 anyway) to bring up the active quests overlay
        events = [
            { "do": "show-quests" }
        ]

        # Emulate each event
        for params in events:

            self.handle_selection(params, [], network_controller, universe, universe.get_active_map(), universe.session, widget_dispatcher, text_renderer, None)


        # Now we need to cursor onto the RowMenu item that pertains to the quest in question.
        # Begin by fetching the RowMenu, which is the left panel of the now-visible "active quests" overlay.
        overlay = self.get_overlay_item_by_id("active-quests")

        if (overlay):

            # Grab the RowMenu
            row_menu = overlay.get_widget().item1

            # Get the row item that corresponds with the provided quest
            widget = row_menu.get_widget_by_id(quest_name)

            # Set the cursor at that position...
            if (widget):

                # Set cursor
                row_menu.set_cursor_at_widget(widget)


    # Build the widget
    def handle_build_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the menu controller;
        menu_controller = control_center.get_menu_controller()

        # and the splash controller;
        splash_controller = control_center.get_splash_controller()

        # and the default text renderer.
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


        # Pause the game if we're freshly creating this pause menu
        if (self.first_build):

            # Pause
            universe.pause()


        # Pause lock the menu controller.  Can't be pausing the game while the game is paused...
        menu_controller.configure({
            "pause-locked": True
        })


        # Call in the pause splash
        splash_controller.set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # Fetch the pause menu template
        template = self.fetch_xml_template("gamemenu").add_parameters({
           "@width": xml_encode( "%d" % self.width )
        })

        # Compile the template
        root = template.compile_node_by_id("menu")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)


        """ start hack """
        navbar = widget.get_widget_by_id("navbar")

        navbar.slide(DIR_LEFT, percent = 0.6, animated = False)
        navbar.slide(None)


        # Give focus to the HMenu navbar at first
        widget.set_active_widget_by_id("navbar")


        #widget_stack.set_attribute("first-load", "yes")
        widget.set_attribute("first-load", "no")

        # Get the name of the tab we want to show
        tab_name = navbar.get_active_widget().get_attribute("rel")#value()


        # Remove the active GridMenu from the MenuStack (if there is one)...
        widget.remove_widget_by_id("content")

        # Add the appropriate GridMenu to the MenuStack.  Do this immediately.
        widget.add_widget_with_id(
            self.create_tab(
                tab_name,
                control_center,
                universe
            ),
            "content",
            text_renderer
        )

        # Convenience
        row_menu = widget.get_widget_by_id("content")

        # Force focus on the first available element
        row_menu.set_cursor(0)

        a = time.time()
        row_menu.blur()



        row_menu.slide(DIR_RIGHT, percent = 0.6, animated = False)
        row_menu.slide(None)

        """ end hack """


        widget.set_id("root")

        # Add the MenuStack as the first overlay
        results.append(
            self.add_widget_via_event(widget, event)
        )


        # We've definitely completed the first build, if not an iterative (refresh) build...
        self.first_build = False

        # Return events
        return results


    # Navbar wrap down
    def handle_navbar_wrap_down_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Convenience
        hmenu = params["widget"]

        # Disable focus for the hmenu...
        hmenu.blur()

        # In our menu stack (overlay id "root"), give focus to index 1 (the GridMenu).
        # Do this as a queue task, though, to prevent a "double tap" as we have not actually
        # processed the seconds MenuStack item yet...
        self.queue(
            lambda a = self.get_widget_by_id("root"): a.set_active_widget_by_id("content")
        )

        # Force focus on the first available element
        self.get_widget_by_id("root").get_widget_by_id("content").set_cursor( (0, 0) )



    # Navbar cursor change
    def handle_navbar_change_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the default text renderer
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


        # Convenience
        hmenu = params["widget"]

        # Get the name of the tab we want to show
        tab_name = hmenu.get_active_widget().get_attribute("rel")#value()


        # Remove the active GridMenu from the MenuStack (if there is one)...
        self.get_widget_by_id("root").remove_widget_by_id("content")

        # Add the appropriate GridMenu to the MenuStack.  Do this immediately.
        self.get_widget_by_id("root").add_widget_with_id(
            self.create_tab(
                tab_name,
                control_center,
                universe
            ),
            "content",
            text_renderer
        )

        # Convenience
        row_menu = self.get_widget_by_id("root").get_widget_by_id("content")

        # Force focus on the first available element
        row_menu.set_cursor(0)

        row_menu.blur()



        if ( self.get_widget_by_id("root").get_attribute("first-load") == "yes" ):

            row_menu.slide(DIR_RIGHT, percent = 0.6, animated = False)
            row_menu.slide(None)

            self.get_widget_by_id("root").set_attribute("first-load", "no")


        snapshot = self.history_controller.load_snapshot_by_id("pause-menu")
        if (snapshot):
            grid_menu.set_state(snapshot)

        # Return events
        return results


    # Active tab wrap down event
    def handle_tab_wrap_down_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Convenience
        row_menu = params["widget"]

        # Remove focus from the GridMenu
        row_menu.blur()

        # If we wrapped "down," then we're going to reset the cursor to (0, 0)
        row_menu.set_cursor(0)


        # Give focus back to the nav bar.  Do this as a queue task, though.
        self.queue(
            lambda a = self.get_widget_by_id("root"): a.set_active_widget_by_id("navbar")
        )

        # Return events
        return results


    # Active tab abort event
    def handle_tab_abort_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Convenience
        row_menu = params["widget"]

        # Remove focus from the GridMenu
        row_menu.blur()


        # Give focus back to the nav bar.  Do this as a queue task, though.
        self.queue(
            lambda a = self.get_widget_by_id("root"): a.set_active_widget_by_id("navbar")
        )

        # Return events
        return results


    # Show a skill tree (2 skills per tree)
    def handle_show_skill_tree_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Fetch the base directory template
        template = self.fetch_xml_template("skills.tree.directory").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("directory")


        # Track zebra on skill tree directory
        zebra = False

        # We need to load in and inject insert data for the 2 skills in this tree...
        for skill in SKILLS_BY_CATEGORY[ params["param"] ]:

            # Info on this skill...
            (category, level, is_locked) = (
                CATEGORIES_BY_SKILL[skill],
                int( universe.get_session_variable("core.skills.%s" % skill).get_value() ),
                (int( universe.get_session_variable("core.skills.%s:locked" % skill).get_value() ) == 1)
            )

            # If this skill is "locked," then we set it at level "-1" for UI purposes...
            if (is_locked):

                level = level#-1


            log( skill, category, level, is_locked )

            # Fetch stats for the next skill level (required character level, etc.)
            stats = universe.get_skill_stats().get_skill_stats_by_level(skill, min( (level + 1), universe.get_skill_stats().get_skill_max_level(skill) ) )

            # If the skill is locked (level -1), we will use level 1 description / min-level data
            if (is_locked):

                stats = universe.get_skill_stats().get_skill_stats_by_level(skill, 1)


            # Which tier should we fetch label data for?
            # Which template version will we want for the options pane?
            (tier, template_version) = (
                "locked", # Assume locked tier (i.e. "this skill is locked")
                "locked"  # Assume locked button options (i.e. only a cancel button)
            )

            if (not is_locked):

                # Maxed?
                if ( level >= universe.get_skill_stats().get_skill_max_level(skill) ):

                    (tier, template_version) = (
                        "max",
                        "max"
                    )

                # Still able to unlock / upgrade...
                else:

                    (tier, template_version) = (
                        "%d" % (level + 1), # View next level stats
                        "upgrade" if (level == 0) else "upgrade" # Unlock / upgrade skill; it's not maxed or locked...
                    )


            # Zebra version?
            if (zebra):

                template_version = "%s:zebra" % template_version



            # Fetch (and compile) the label / gif source data for the given skill, stored in an XML template on a skill-by-skill basis
            info_node = XMLParser().create_node_from_xml(
                self.fetch_xml_template_from_path(
                    "%s" % skill,
                    universe.get_working_skill_data_path()
                ).template
            ).get_first_node_by_tag("*").get_first_node_by_tag(
                "data",
                {
                    "tier": tier
                }
            ).get_first_node_by_tag("texts")


            # Loop each of the inserts
            for name in ("header", "content"):

                # Fetch the skill insert template (either the header or the content field).
                # Some of these parameters apply to one, some to the other.  I'm redundantly supplying the both (lazy).
                template = self.fetch_xml_template( "skills.tree.directory.insert", version = template_version + ":%s" % name ).add_parameters({
                    "@skill-name": xml_encode( skill ),
                    "@skill-title": xml_encode( SKILL_LABELS[skill] ),
                    "@skill-level": xml_encode( "%d" % (level + 1) ),
                    "@required-skill-points": xml_encode( "%d" % stats.get_cost() ),
                    "@necessary-skill-points-pluralizer": xml_encode( "s" if ( stats.get_cost() != 1 ) else "" ),
                    "@skill-overview": xml_encode( localization_controller.translate( info_node.get_first_node_by_tag("overview").innerText ) ),
                    "@skill-specs": xml_encode( info_node.find_node_by_tag("specs").innerText ),
                    "@gif-source": xml_encode( info_node.find_node_by_tag("gif-data").find_node_by_tag("map").innerText ),
                    "@replay-file": xml_encode( info_node.find_node_by_tag("gif-data").find_node_by_tag("replay-file").innerText ),
                    "@active-skill": xml_encode( info_node.find_node_by_tag("gif-data").find_node_by_tag("active-skill").innerText ),
                    "@button-width": xml_encode( "%d" % SKILL_PREVIEW_WIDTH ) # for buttons that want to mirror the gif's width...
                })

                # Compile insert
                node2 = template.compile_node_by_id("insert-%s" % name)

                # Insert items within wrapper, if we found any inserts
                if (node2):

                    # item-groups do not implicitly run their associated translations.
                    # Here we'll share those with the item group's children...
                    for ref_child in node2.get_nodes_by_tag("*"):

                        # Hacky share
                        ref_child.set_data(
                            "translations",
                            node2.get_data("translations")
                        )

                    root.add_node(node2)
                    logn( "pause-menu", (node2, node2.get_data("translations")) )

            """
            markup = self.parameterize_xml_template(
                template,
                {
                    "@skill-name": xml_encode( skill ),
                    "@skill-title": xml_encode( SKILL_LABELS[skill] ),
                    "@next-level": xml_encode( "%d" % (level + 1) ),
                    "@gif-source": xml_encode( info_node.get_first_node_by_tag("gif-source").innerText )
                }
            )
            """

            # Stripe zebra
            zebra = (not zebra)

        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("skill-tree-directory")

        # Add the directory!
        results.append(
            self.add_widget_via_event(widget, event)
        )

        # Return events
        return results


    # Show the options for a given skill (insert) in a skill tree
    def handle_show_skill_tree_insert_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the default text renderer
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


        # Which skill are we showing options for?
        skill = params["skill"]

        log2( "show options for:  ", skill )

        """ Shift existing page """
        # Fetch the skill tree directory, the current page
        directory = self.get_widget_by_id("skill-tree-directory")

        # Fetch all of the item groups
        groups = directory.get_groups()


        # I'm going to keep track of which of those groups is related to the selected skill (should find 2 of them, I think)
        relevant_group_indices = []

        # Loop the groups, tracking the relevant ones and hiding the others...
        for i in range( 0, len(groups) ):

            log2( "group %d" % i, "rel = %s" % groups[i].get_rel(), groups[i].attributes )

            # Check the rel attribute, make sure it's equal to the selected skill
            if ( groups[i].get_rel() == skill ):

                # Track it as a relevant group
                relevant_group_indices.append(i)

            # Irrelevant groups fade away
            else:

                # Slide and hide
                #groups[i].slide(DIR_LEFT, percent = 1.0)
                groups[i].hide()

        log2( relevant_group_indices )


        # Calculate the current relative y offset of the first relevant group we found (the highest in the directory).
        # **We're going to keep track of this dy in the new page we create, by the way, so that we can
        #   "undo" the shift we apply to this relevant groups when we're done...
        dy = min( directory.get_y_offset_at_index( text_renderer, directory.get_group_first_item_index_by_group_index(index) ) - directory.get_scroll_offset_at_item_index(directory.cursor, text_renderer) for index in relevant_group_indices ) # Crazy!


        # Slide any relevant groups up by that amount, moving them to the top of the screen
        for index in relevant_group_indices:

            # Slide up
            groups[index].slide(DIR_UP, amount = dy)


        # Lastly, I need to know the cumulative height of each of the relevant groups so that I know
        # where to position the new page (immediately below the relevant groups).
        new_page_y = sum( groups[index].get_box_height(text_renderer) for index in relevant_group_indices )



        #row_menu = self.get_widget_by_id("skill-tree-directory")

        # From that directory, fetch the active "group" (just one item, but framed) so that we can slide it out of the way
        #group = row_menu.get_active_group()

        # Validate
        #if (group):

        #    # Slide and hide
        #    group.slide(DIR_LEFT, amount = PAUSE_MENU_WIDTH)
        #    group.hide()


        """ Fetch stats and stuff for skill selected """
        # Info on this skill...
        (category, level, is_locked) = (
            CATEGORIES_BY_SKILL[skill],
            int( universe.get_session_variable("core.skills.%s" % skill).get_value() ),
            (int( universe.get_session_variable("core.skills.%s:locked" % skill).get_value() ) == 1)
        )

        # If this skill is "locked," then we set it at level "-1" for UI purposes...
        if (is_locked):

            level = -1


        # Fetch stats for the next skill level (required character level, etc.)
        stats = universe.get_skill_stats().get_skill_stats_by_level(skill, min( (level + 1), universe.get_skill_stats().get_skill_max_level(skill) ) )

        # If the skill is locked (level -1), we will use level 1 description / min-level data
        if (is_locked):

            stats = universe.get_skill_stats().get_skill_stats_by_level(skill, 1)


        # Which tier should we fetch label data for?
        # Which template version will we want for the options pane?
        (tier, template_version) = (
            "locked", # Assume locked tier (i.e. "this skill is locked")
            "locked"  # Assume locked button options (i.e. only a cancel button)
        )

        if (not is_locked):

            # Maxed?
            if ( level >= universe.get_skill_stats().get_skill_max_level(skill) ):

                (tier, template_version) = (
                    "max",
                    "max"
                )

            # Still able to unlock / upgrade...
            else:

                (tier, template_version) = (
                    "%d" % (level + 1), # View next level stats
                    "new" if (level == 0) else "upgrade" # Unlock / upgrade skill; it's not maxed or locked...
                )


        # Fetch (and compile) the label / gif source data for the given skill, stored in an XML template on a skill-by-skill basis
        info_node = XMLParser().create_node_from_xml(
            self.fetch_xml_template_from_path(
                "%s" % skill,
                universe.get_working_skill_data_path()
            ).template
        ).get_first_node_by_tag("*").get_first_node_by_tag(
            "data",
            {
                "tier": tier
            }
        ).get_first_node_by_tag("texts")


        """ Build widget """
        # Fetch the "upgrade options" template
        template = self.fetch_xml_template( "skills.tree.directory.insert.options", version = template_version ).add_parameters({
            "@y": xml_encode( "%d" % new_page_y ),#( row_menu.get_y_offset_at_index(text_renderer, row_menu.cursor) - row_menu.get_scroll_offset_at_item_index(row_menu.cursor, text_renderer) ) ), # whew!
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % 200 ),#directory.get_active_widget().get_box_height(text_renderer) ), # hard-coded, temporary... use same width as widget we just slid away...
            "@skill-icon-index": xml_encode( "%d" % SKILL_ICON_INDICES[skill] ),
            "@skill-name": xml_encode( skill ),
            "@skill-title": xml_encode( SKILL_LABELS[skill] ),
            "@skill-level": xml_encode( "%d" % (level + 1) ),
            "@skill-details": xml_encode( info_node.get_first_node_by_tag("specs").innerText ),
            "@button-width": xml_encode( "%d" % SKILL_PREVIEW_WIDTH ) # no gif, but this allows for parallelism in the ui
        })

        # Compile template
        root = template.compile_node_by_id("options")


        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("skill-tree-insert-options")


        # Remember, the new widget needs to keep track of the amount we shifted the "relevant groups" by
        # so that we can can "undo" that shift on page back.
        widget.set_attribute("-dy", "%s" % dy) # We'll cast back to integer when we're ready to use it...


        # Position the widget offscreen, then instruct it to slide into view...
        widget.slide(DIR_DOWN, amount = 200, animated = False)
        widget.slide(None)

        # Add overlay
        results.append(
            self.add_widget_via_event(widget, event, exclusive = False)
        )

        # Return events
        return results


    # Hide the options for a skill within a skill tree (abort)
    def handle_hide_skill_tree_insert_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get the page with the options on it
        widget = self.get_widget_by_id("skill-tree-insert-options")

        # Get a handle to the directory page (the page before the options, with the irrelevant portions faded away)
        directory = self.get_widget_by_id("skill-tree-directory")

        # Loop its groups
        for group in directory.get_groups():

            # Make sure each group is visible, now that we're returning to the overall directory page
            group.show()

            # Also, make sure we group returns to its default location (i.e. no slide)
            group.slide(None)


        # Hide the options page
        widget.hide()

        # Slide it down off the screen
        widget.slide(
            DIR_DOWN,
            amount = SCREEN_HEIGHT,
            on_complete = "previous-page"
        )

        # Return events
        return results


    # Show the confirm upgrade page for a given skill tree option ("Are you sure you want to upgrade?" or "You don't have enough points" or whatever)
    def handle_show_skill_tree_insert_options_upgrade_confirm_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Skill name?
        skill = params["skill"]

        # Category?
        category = CATEGORIES_BY_SKILL[skill]

        # Current player character level
        character_level = int( universe.get_session_variable("core.player1.level").get_value() )

        # Current level of that skill (before upgrade!)?
        current_skill_level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )

        # Next upgrade level?
        next_skill_level = int( params["level"] )

        # Fetch stats for the next skill level (required character level, etc.)
        stats = universe.get_skill_stats().get_skill_stats_by_level(skill, next_skill_level)


        # Our alert (be it error, confirmation, or whatever) will have some n number of items/item-groups...
        root = None

        # If we have no skill points, we cannot upgrade...
        if ( int( universe.get_session_variable("core.player1.skill-points").get_value() ) < stats.get_cost() ):

            # Fetch the nopoints template
            template = self.fetch_xml_template("skills.upgrades.nopoints").add_parameters({
                "@x": xml_encode( "%d" % 0 ),
                "@y": xml_encode( "%d" % 0 ),
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@skill-name": xml_encode(skill),
                "@skill-title-and-level": xml_encode( "%s %s" % (SKILL_LABELS[skill], next_skill_level) ),
                "@skill-level": xml_encode( "%d" % next_skill_level ),
                "@skill-points-available": xml_encode( universe.get_session_variable("core.player1.skill-points").get_value() ),
                "@pluralizer": xml_encode( "s" * int( ( int( universe.get_session_variable("core.player1.skill-points").get_value() ) != 1) ) ), # 1 point vs 2 points
                "@current-character-level": xml_encode( "%d" % character_level ),
                "@required-skill-points": xml_encode( "%d" % stats.get_cost() ),
                "@necessary-skill-points-pluralizer": xml_encode( "s" if ( stats.get_cost() != 1 ) else "" )
            })

            # Compile template
            root = template.compile_node_by_id("alert")


        # If we aren't a high enough character level, we can't unlock/upgrade this skill...
        elif ( character_level < stats.get_min_character_level() ):

            # Fetch "not available yet" template
            template = self.fetch_xml_template("skills.upgrades.na").add_parameters({
                "@x": xml_encode( "%d" % 0 ),
                "@y": xml_encode( "%d" % 0 ),
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@skill-name": xml_encode(skill),
                "@skill-title-and-level": xml_encode( "%s %s" % (SKILL_LABELS[skill], next_skill_level) ),
                "@skill-level": xml_encode( "%d" % next_skill_level ),
                "@skill-points-available": xml_encode( universe.get_session_variable("core.player1.skill-points").get_value() ),
                "@pluralizer": xml_encode( "s" * int( ( int( universe.get_session_variable("core.player1.skill-points").get_value() ) != 1) ) ), # 1 point vs 2 points
                "@current-character-level": xml_encode( "%d" % character_level ),
                "@required-skill-points": xml_encode( "%d" % stats.get_cost() ),
                "@necessary-skill-points-pluralizer": xml_encode( "s" if ( stats.get_cost() != 1 ) else "" )
            })

            # Compile template
            root = template.compile_node_by_id("alert")


        # If everything checks out, let's just get final confirmation from the player...
        else:

            # Fetch the confirmation template
            template = self.fetch_xml_template("skills.upgrades.confirm").add_parameters({
                "@x": xml_encode( "%d" % 0 ),
                "@y": xml_encode( "%d" % 0 ),
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@skill-name": xml_encode(skill),
                "@skill-title-and-level": xml_encode( "%s %s" % (SKILL_LABELS[skill], next_skill_level) ),
                "@skill-level": xml_encode( "%d" % next_skill_level ),
                "@skill-points-available": xml_encode( universe.get_session_variable("core.player1.skill-points").get_value() ),
                "@pluralizer": xml_encode( "s" * int( ( int( universe.get_session_variable("core.player1.skill-points").get_value() ) != 1) ) ) # 1 point vs 2 points
            })

            # Compile the template into an XML node
            root = template.compile_node_by_id("alert")



        # Fetch (and compile) the label / gif source / injection data for the given skill, stored in an XML template on a skill-by-skill basis
        info_node = XMLParser().create_node_from_xml(
            self.fetch_xml_template_from_path(
                "%s" % skill,
                universe.get_working_skill_data_path()
            ).template
        ).get_first_node_by_tag("*").get_first_node_by_tag(
            "data",
            {
                "tier": "%d" % next_skill_level
            }
        ).get_first_node_by_tag("texts")


        # Check to see if we have any injections while "confirming."
        ref_injections = info_node.get_first_node_by_tag("inserts").get_first_node_by_tag("confirm")

        # Validate
        if (ref_injections):

            # Fetch all injections
            injection_collection = ref_injections.get_nodes_by_tag("*")

            for target_id in ("ext.header", "ext.footer"):

                # Find the corresponding target node in the template
                ref_target = root.find_node_by_id(target_id)

                # Validate
                if (ref_target):

                    # Check each injection to see if it belongs here...
                    for ref_injection in injection_collection:

                        # Does the injections node have anything for this injection group?
                        if ( ref_target.get_attribute("rel") == ref_injection.tag_type ):

                            # Fetch a generic injection template
                            template = self.fetch_xml_template("generic.injection").add_parameters({
                                "@text": xml_encode( localization_controller.translate( ref_injection.innerText ) )
                            })

                            # Add compiled injection
                            ref_target.add_node(
                                template.compile_node_by_id("container")
                            )


        # Let's finally create a prompt to get the player's decision...
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("prompt-confirm-skill-upgrade")


        # Slide previous pages away
        for page_name in ("skill-tree-directory", "skill-tree-insert-options"):

            # Fetch page
            page = self.get_widget_by_id(page_name)

            # Slide and hide
            page.slide(DIR_UP, amount = 200)
            page.hide()


        # Position confirmation to slide in from the left
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Now bring it into view
        widget.slide(None)


        # Lastly, add the overlay!
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the upgrade confirmation page for a skill in a skill tree
    def handle_hide_skill_tree_insert_options_upgrade_confirm_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Slide previous pages back into their default locations
        for page_name in ("skill-tree-directory", "skill-tree-insert-options"):

            # Fetch page
            page = self.get_widget_by_id(page_name)

            # Slide back in, show page
            page.slide(None)
            page.show()


        # Fetch the original skill tree directory (2 pages back!)
        directory = self.get_widget_by_id("skill-tree-directory")

        # Loop groups
        for group in directory.get_groups():

            # We want to show and unslide any group relevant to the skill we were on...
            if ( group.get_rel() != params["skill"] ):

                # Hide this irrelevant group
                group.hide()


        # Get the active page
        widget = self.get_active_page()

        # Slide and hide
        widget.slide(DIR_DOWN, amount = SCREEN_HEIGHT)
        widget.hide(
            on_complete = "previous-page"
        )

        # Return events
        return results


    # Commit an upgrade to a given skill
    def handle_commit_skill_tree_insert_options_upgrade_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get the skill name
        skill = params["skill"]

        # Which level will we be upgrading to?
        level = int( params["level"] )


        # Get the opposite skill's name...
        opposite_skill = SKILL_OPPOSITES[skill]

        # Ensure that the opposite skill is locked...
        universe.set_session_variable("core.skills.%s:locked" % opposite_skill, "1")


        # Get the current skill points available count
        skill_points_available = int( universe.get_session_variable("core.player1.skill-points").get_value() )


        # Just a little sanity testing...
        current_skill_level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )

        if (current_skill_level < level):

            # Fetch stats for the newly reached skill level
            stats = universe.get_skill_stats().get_skill_stats_by_level(skill, level)


            # Upgrade chosen skill to the specified level...
            universe.set_session_variable("core.skills.%s" % skill, "%d" % level)

            # Reduce skill points available
            universe.increment_session_variable( "core.player1.skill-points", -1 * stats.get_cost() )


            # If we're freshly unlocking the skill, then increment the universe's stat counter
            if (current_skill_level == 0):

                # Increment stat counter
                universe.get_session_variable("stats.skills-unlocked").increment_value(1)

                # Execute the "unlocked-skill" achievement hook
                universe.execute_achievement_hook( "unlocked-skill", control_center )


            # Always execute the "upgraded-skill" achievement hook
            universe.execute_achievement_hook( "upgraded-skill", control_center )

            # Also execute the "upgraded-skill-to-level-#" achievement hook
            universe.execute_achievement_hook( "upgraded-skill-to-level-%d" % level, control_center )


            # Post a newsfeeder item updating the player
            control_center.get_window_controller().get_newsfeeder().post({
                "type": (NEWS_SKILL_UNLOCKED if (level == 1) else NEWS_SKILL_UPGRADED),
                "skill-title": SKILL_LABELS[skill],
                "skill-level": "%d" % level,
                "skill-points-remaining": "%s" % universe.get_session_variable("core.player1.skill-points").get_value()
            })


            # If the player does not have a skill assigned to slot 1 yet,
            # automatically equip this skill in slot 1.
            if ( universe.get_session_variable("core.player1.skill1").get_value() == "" ):

                # Get local player
                player = universe.get_local_player()

                # Validate
                if (player):

                    # Equip skill to slot 1
                    player.equip_skill_in_slot(skill, 1, control_center, universe)

                # Post a newsfeeder message letting the player know which
                # key to press to use the skill.
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": control_center.get_localization_controller().get_label( "skill-n-equipped:title", { "@n": SKILL_LABELS[skill] } ),
                    "content": control_center.get_localization_controller().get_label( "press-n-to-use-skill:message", {
                        "@n": "%s" % ( universe.get_session_variable("sys.input.keyboard.skill1").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.skill1").get_value() )
                    } )
                })

            # Run the same check for slot 2
            elif ( universe.get_session_variable("core.player1.skill2").get_value() == "" ):

                # Get local player
                player = universe.get_local_player()

                # Validate
                if (player):

                    # Equip skill to slot 1
                    player.equip_skill_in_slot(skill, 2, control_center, universe)

                # Post a newsfeeder message letting the player know which
                # key to press to use the skill.
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": control_center.get_localization_controller().get_label( "skill-n-equipped:title", { "@n": SKILL_LABELS[skill] } ),
                    "content": control_center.get_localization_controller().get_label( "press-n-to-use-skill:message", {
                        "@n": "%s" % ( universe.get_session_variable("sys.input.keyboard.skill2").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.skill2").get_value() )
                    } )
                })


        # Rebuild menus to reflect the upgrade...
        self.refresh_pages(control_center, universe, curtailed_count = 1)#user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, curtailed_count = 1)


        # Flag any currently active response menu to rebuild itself to reflect potential persuasion/hacking upgrades...
        universe.set_session_variable("app.rebuild-response-menu", "1")

        # Return events
        return results


    # Show all skills a player has acquired, allow them to assign skills to hotkeys
    def handle_show_game_skills_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # How many ACTIVE skills have we unlocked?  Any?
        skills_unlocked_count = sum( (int( universe.get_session_variable("core.skills.%s" % e).get_value() ) > 0) for e in ACTIVE_SKILL_LIST )


        # Fetch the template that defines the left pane (option panel)
        template = self.fetch_xml_template("game.skills").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@skills-unlocked-count": xml_encode( "%d" % skills_unlocked_count )
        })

        # Compile the template
        root = template.compile_node_by_id("directory")


        # Zebra tracking as we list equipped skills (or free slots)
        zebra = False

        # Loop through "n" skill slots, adding in a button to represent each one...
        for slot in range(1, MAX_SKILL_SLOTS + 1):

            # Which skill (if any) occupies this slot?
            skill = universe.get_session_variable("core.player1.skill%d" % slot).get_value()

            # Current level for this skill?
            level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )


            # If this skill validates, then we have an equipped skill...
            if (skill in ACTIVE_SKILL_LIST):

                # Fetch (and compile) the label / gif source data for the given skill, stored in an XML template on a skill-by-skill basis
                info_node = XMLParser().create_node_from_xml(
                    self.fetch_xml_template_from_path(
                        "%s" % skill,
                        universe.get_working_skill_data_path()
                    ).template
                ).find_node_by_id( "%s" % skill ).get_first_node_by_tag(
                    "data",
                    {
                        "tier": "%d" % level
                    }
                ).get_first_node_by_tag("texts")


                # Translate manual text
                skill_manual = self.parameterize_xml_template(
                    localization_controller.translate( info_node.find_node_by_tag("manual").innerText ),
                    {
                        "@key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.skill%d" % slot).get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.skill%d" % slot).get_value() ) )
                    }
                )


                # Fetch the appropriate template for this skill slot
                template = self.fetch_xml_template( "game.skills.equipped.insert", version = ("equipped" if (not zebra) else "equipped:zebra") ).add_parameters({
                    "@skill-icon-index": xml_encode( "%d" % SKILL_ICON_INDICES[skill] ),
                    "@skill-title": xml_encode( SKILL_LABELS[skill] ),
                    "@skill-key": xml_encode( "slot %d" % slot ),
                    "@skill-name": xml_encode( skill ),
                    "@skill-manual": xml_encode( "%s" % skill_manual ),
                    "@slot": xml_encode( "%d" % slot ),
                })

                # Compile and add to the template
                root.find_node_by_id("ext.equipped-skills").add_node(
                    template.compile_node_by_id("insert")
                )

            else:

                # Fetch the "no skill equipped" template
                template = self.fetch_xml_template( "game.skills.equipped.insert", version = ("not-equipped" if (not zebra) else "not-equipped:zebra") ).add_parameters({
                    "@skill-icon-index": xml_encode( "%d" % 13 ), # hard-coded
                    "@slot": xml_encode( "%d" % slot )
                })

                # Compile and add to the template
                root.find_node_by_id("ext.equipped-skills").add_node(
                    template.compile_node_by_id("insert")
                )

            # Stripe our zebra friend
            zebra = (not zebra)


        # Zebra tracking as we prepare to list every acquired skill
        zebra = False

        # Loop through all acquired skills, adding them in the "active skills" list
        for skill in ACTIVE_SKILL_LIST:

            # Current level?
            level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )

            logn( "pause-menu skills", skill, level )

            # Unlocked yet?
            if (level > 0):

                # Fetch (and compile) the label / gif source data for the given skill, stored in an XML template on a skill-by-skill basis
                info_node = XMLParser().create_node_from_xml(
                    self.fetch_xml_template_from_path(
                        "%s" % skill,
                        universe.get_working_skill_data_path()
                    ).template
                ).find_node_by_id( "%s" % skill ).get_first_node_by_tag(
                    "data",
                    {
                        "tier": "%d" % level
                    }
                ).get_first_node_by_tag("texts")


                # Default to not-equipped template
                template_version = "not-equipped"

                # Perhaps, though, this skill IS equipped?
                if ( universe.is_skill_equipped(skill) ):

                    # Different template
                    template_version = "equipped"


                # Zebra template?
                if (zebra):

                    # Stripe
                    template_version = "%s:zebra" % template_version


                # Fetch the template for each iter
                template = self.fetch_xml_template( "game.skills.all.insert", version = template_version ).add_parameters({
                    "@skill-icon-index": xml_encode( "%d" % SKILL_ICON_INDICES[skill] ),
                    "@skill-name": xml_encode( skill ),
                    "@skill-title": xml_encode( SKILL_LABELS[skill] ),
                    "@skill-level": xml_encode( "%d" % level ),
                    "@skill-specs": xml_encode( info_node.get_first_node_by_tag("specs").innerText )
                })

                # Compile and add to the template
                root.find_node_by_id("ext.all-skills").add_node(
                    template.compile_node_by_id("insert")
                )

                #print template.compile_node_by_id("insert")#root.compile_xml_string()
                #print template.compile_node_by_id("insert").compile_xml_string()


                # Stripe zebra
                zebra = (not zebra)


        #log2( root.compile_xml_string() )

        # Create the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("skills.equip.directory")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show the options available for a given equipped skill slot (i.e. pick a skill for that slot)
    def handle_show_game_skills_equipped_insert_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # How many ACTIVE skills have we unlocked?  Any?
        active_skills_unlocked_count = sum( (int( universe.get_session_variable("core.skills.%s" % e).get_value() ) > 0) for e in ACTIVE_SKILL_LIST )

        # Prepare to create a root node
        root = None


        # Any active skill unlocked?
        if (active_skills_unlocked_count > 0):

            # Fetch the appropriate version of the "options menu" for ths selected skill slot
            template = self.fetch_xml_template( "game.skills.equipped.insert.options", version = ("normal" if (active_skills_unlocked_count > 0) else "no-active-skill") ).add_parameters({
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT )
            })

            # Compile template
            root = template.compile_node_by_id("menu")


            # Now we need to add all currently acquired skills to the template...
            for skill in ACTIVE_SKILL_LIST:

                # Current level?
                level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )

                # Unlocked yet?
                if (level > 0):

                    # Fetch the template for each skill
                    template = self.fetch_xml_template("game.skills.equipped.insert.options.skill").add_parameters({
                        "@skill-icon-index": xml_encode( "%d" % SKILL_ICON_INDICES[skill] ),
                        "@skill-name": xml_encode( skill ),
                        "@skill-title": xml_encode( SKILL_LABELS[skill] ),
                        "@slot": xml_encode( params["slot"] )
                    })

                    # Compile template
                    node = template.compile_node_by_id("insert")

                    # Add it to the main template
                    root.find_node_by_id("ext.active-skills").add_node(node)


        # We haven't unlocked any active skill.  We might have unlocked a passive skill, but that's irrelevant here...
        else:

            # Fetch the appropriate template...
            template = self.fetch_xml_template( "game.skills.equipped.insert.options", version = "no-active-skill" ).add_parameters({
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT )
            })

            # Compile template
            root = template.compile_node_by_id("menu")


        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("skills-directory-skill-options")


        # Handle to main page
        page1 = self.get_widget_by_id("skills.equip.directory")

        # Slide it to the appropriate side, thne position the new page offscreen to that side...
        if ( params["side"] == "left" ):

            # Slide right
            page1.slide(DIR_RIGHT, amount = widget.get_width() + 20)


            # Position new page offscreen, with padding
            widget.slide(DIR_LEFT, percent = 1.1, animated = False)

            # Now set it to slide back to default
            widget.slide(None)

        elif ( params["side"] == "right" ):

            # Slide main page left
            page1.slide(DIR_LEFT, amount = widget.get_width() + 20)


            # Position new page offscreen, with padding
            widget.slide(DIR_RIGHT, amount = page1.get_width() + 20, animated = False)

            # Restore to default, with animation
            widget.slide(DIR_RIGHT, amount = page1.get_width() - widget.get_width() + 20)


        # Remember which side we're on...
        widget.set_attribute("side", params["side"])


        # Lastly, add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the options page for an equipped skill insert
    def handle_hide_game_skills_equipped_insert_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get the 2 visible pages
        (page1, page2) = (
            self.get_widget_by_id("skills.equip.directory"),
            self.get_widget_by_id("skills-directory-skill-options")
        )


        # Which side did we show the menu on?
        side = page2.get_attribute("side")


        # Left?
        if (side == "left"):

            # Slide and hide the top page
            page2.slide(DIR_LEFT, percent = 1.0)
            page2.hide(
                on_complete = "previous-page"
            )

        # Right?
        elif (side == "right"):

            # Slide it back offscreen east
            page2.slide(DIR_RIGHT, percent = 1.0, incremental = True)
            page2.hide(
                on_complete = "previous-page"
            )


        # Slide main directory back to default position
        page1.slide(None)

        # Return events
        return results


    # Show the options for one of the skills in the "all skills" section
    def handle_show_game_skills_all_insert_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Which skill are we showing the options for?
        skill = params["equipped-skill"]


        # How many ACTIVE skills have we unlocked?  Any?
        skills_unlocked_count = sum( (int( universe.get_session_variable("core.skills.%s" % e).get_value() ) > 0) for e in ACTIVE_SKILL_LIST )

        # Prepare to create a root node
        root = None


        # Any active skill unlocked?
        if (skills_unlocked_count > 0):

            # Fetch the appropriate version of the "options menu" for ths selected skill
            template = self.fetch_xml_template( "game.skills.all.insert.options", version = params["template-version"] ).add_parameters({
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@skill-name": xml_encode( skill )
            })

            # Compile template
            root = template.compile_node_by_id("menu")


            """
            # Now we need to add all currently acquired skills to that template...
            for skill in ACTIVE_SKILL_LIST:

                # Current level?
                level = int( universe.get_session_variable("core.skills.%s" % skill).get_value() )

                # Unlocked yet?
                if (level > 0):

                    # Fetch the template for each iter
                    template = self.fetch_xml_template("skills.assign.option").add_parameters({
                        "@skill-icon-index": xml_encode( "%d" % SKILL_ICON_INDICES[skill] ),
                        "@skill-name": xml_encode( skill ),
                        "@skill-title": xml_encode( SKILL_LABELS[skill] ),
                        "@slot": xml_encode( params["slot"] )
                    })

                    # Compile template
                    iter_node = XMLParser().create_node_from_xml(markup).???

                    # Inject the node into the appropriate root...
                    root.get_first_node_by_tag("template").get_node_by_id("ext.active-skills").add_nodes( iter_node.get_first_node_by_tag("template").get_nodes_by_tag("*") )
            """


        # We haven't unlocked any active skill.  We might have unlocked a passive skill, but that's irrelevant here...
        else:

            # Fetch the appropriate template...
            template = self.fetch_xml_template( "skills.assign.directory", version = "na" ).add_parameters({
            })

            # Compile template
            root = XMLParser().create_node_from_xml(markup)


        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("skills-directory-skill-options")


        # Handle to main page
        page1 = self.get_widget_by_id("skills.equip.directory")

        # Slide it to the appropriate side, thne position the new page offscreen to that side...
        if ( params["side"] == "left" ):

            # Slide right
            page1.slide(DIR_RIGHT, amount = widget.get_width() + 20)


            # Position new page offscreen, with padding
            widget.slide(DIR_LEFT, percent = 1.1, animated = False)

            # Now set it to slide back to default
            widget.slide(None)

        elif ( params["side"] == "right" ):

            # Slide main page left
            page1.slide(DIR_LEFT, amount = widget.get_width() + 20)


            # Position new page offscreen, with padding
            widget.slide(DIR_RIGHT, amount = page1.get_width() + 20, animated = False)

            # Restore to default, with animation
            widget.slide(DIR_RIGHT, amount = page1.get_width() - widget.get_width() + 20)


        # Remember which side we're on...
        widget.set_attribute("side", params["side"])


        # Lastly, add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the options page for one of the "all skills"... skills
    def handle_hide_game_skills_all_insert_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get the 2 visible pages
        (page1, page2) = (
            self.get_widget_by_id("skills.equip.directory"),
            self.get_widget_by_id("skills-directory-skill-options")
        )


        # Which side did we show the menu on?
        side = page2.get_attribute("side")


        # Left?
        if (side == "left"):

            # Slide and hide the top page
            page2.slide(DIR_LEFT, percent = 1.0)
            page2.hide(
                on_complete = "previous-page"
            )

        # Right?
        elif (side == "right"):

            # Slide it back offscreen east
            page2.slide(DIR_RIGHT, percent = 1.0, incremental = True)
            page2.hide(
                on_complete = "previous-page"
            )


        # Slide main directory back to defautl position
        page1.slide(None)

        # Return events
        return results


    # Assign a given skill to a given skill slot (hotkey)
    def handle_commit_game_skills_assign_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Which slot?
        slot = int( params["slot"] )

        # Which skill?
        skill = params["skill"]


        # Get local player
        player = universe.get_local_player()

        # Validate
        if (player):

            # Equip skill to given slot
            player.equip_skill_in_slot(skill, slot, control_center, universe)
        #universe.set_session_variable("core.player1.skill%d" % slot, skill)

        # Update the UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)#user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller)


        # Return events
        return results


    # Show the "save game" directory (create new save, overwrite existing, etc.)
    def handle_show_game_save_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the save controller
        save_controller = control_center.get_save_controller()


        """ Find all saved games """
        # Build a list of any manual save before we create and populate the template...
        path = universe.get_working_save_data_path()

        # List files
        files = os.listdir(path)

        # Track which folders are manual saves...
        matching_files = []

        for each in files:

            # I only care about the manual saves...
            prefix = "manualsave"

            if (each.startswith(prefix)):

                matching_files.append( os.path.join(path, each) )


        # Sort matching files, newest-to-oldest...
        matching_files = sort_files_by_date(matching_files)


        """ Create base directory """
        # Calculate overall gold collection percentage (if/a in overworldD)
        gold_recovered_percentage = 0.0

        # Avoid divide-by-zero error
        if ( universe.count_gold_pieces("overworld") > 0 ):

            # Calculate raw percentage
            gold_recovered_percentage = int(
                ( universe.count_collected_gold_pieces("overworld") / float( universe.count_gold_pieces("overworld") ) * 10000.0 )
            ) / 100.0


        # Fetch the template for the list of saved games (quicksaves, manual saves, headers, etc.)
        template = self.fetch_xml_template("game.save").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@quicksave-slot-count": xml_encode( "%d" % MAX_QUICKSAVE_SLOTS ),
            "@manualsave-slot-count": xml_encode( "%d" % len(matching_files) ),
            "@character-level": xml_encode( "%s" % universe.get_session_variable("core.player1.level").get_value() ),
            "@gold-collected": xml_encode( "%s%%" % safe_round(gold_recovered_percentage, 1) )
        })

        # Compile the directory listing
        root = template.compile_node_by_id("save-game")


        """ Inject quicksaves """
        # Now process any quicksave slot...
        zebra = False

        # Easy lookup
        template_versions_by_zebra = {
            False: "normal",
            True:  "zebra"
        }

        # Loop "n" quicksave slots
        for slot in range(1, MAX_QUICKSAVE_SLOTS + 1):

            # Get the path to potential autosaves for this universe
            path = os.path.join( universe.get_working_save_data_path(), "quicksave%d" % slot )

            # Quickly, let's try to fetch this save's metadata...
            metadata = save_controller.fetch_metadata_from_folder(path, universe)


            # Fetch template for quicksave iter
            template = self.fetch_xml_template( "game.save.quicksave", version = template_versions_by_zebra[zebra] ).add_parameters({
                "@title": xml_encode( metadata["title"] ),
                "@date": xml_encode( metadata["last-modified-date"] ),
                "@quicksave-slot": xml_encode( "%d" % slot ),
                "@thumbnail": xml_encode( os.path.join(path, "thumb.png") ),
                "@trailing-margin": xml_encode( "0" ),
                "@xtrailing-margin": xml_encode( "%d" % ( max(0, (1 + slot - MAX_AUTOSAVE_SLOTS) * 10) ) ),
                "@character-level": xml_encode( "%s" % metadata["character-level"] ),
                "@gold-collected": xml_encode( "%s" % metadata["gold-recovered"] ) # Inconsistent keys, collected -vs- recovered...
            })

            # Compile the node for this iter
            node = template.compile_node_by_id("file")

            # Inject the node into the appropriate root...
            root.find_node_by_id("ext.quicksaves").add_node(node)


            # Toggle zebra
            zebra = (not zebra)


        """ Inject custom saves """
        # Reset zebra tracking
        zebra = False

        # Loop files
        for each in matching_files:

            # Get the path to potential manual saves for this universe
            path = universe.get_working_save_data_path()

            # I only care about the manual saves...
            prefix = os.path.join(path, "manualsave")

            # Quickly, let's try to fetch this save's metadata...
            metadata = save_controller.fetch_metadata_from_folder(each, universe)


            # Fetch manualsave template
            template = self.fetch_xml_template( "game.save.manualsave", version = template_versions_by_zebra[zebra] ).add_parameters({
                "@title": xml_encode( "%s" % metadata["title"] ),
                "@date": xml_encode( "%s" % metadata["last-modified-date"] ),
                "@manualsave-slot": xml_encode( each[len(prefix) : len(each)] ),
                "@thumbnail": xml_encode( os.path.join(each, "thumb.png") ),
                "@character-level": xml_encode( "%s" % metadata["character-level"] ),
                "@gold-collected": xml_encode( "%s" % metadata["gold-recovered"] ) # Inconsistent keys, collected -vs- recovered...
            })

            # Compile this iter's node
            node = template.compile_node_by_id("file")

            # Inject into the appropriate group
            root.find_node_by_id("ext.manualsaves").add_node(node)


            # Toggle zebra
            zebra = (not zebra)


        """ Finish """
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("save-game")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Officially add the overlay...
        self.add_widget_via_event(widget, event)


        widget.focus()

        # Return events
        return results


    # Transition from a widget to the "save game" keyboard
    def handle_transition_save_game_keyboard_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get active page we're transitioning from
        widget = self.get_active_page()


        # We need the default keyboard value and the slot we're saving to,
        # because this is used to overwrite existing custom saves.
        (save_title, save_slot) = (
            widget.get_attribute( "-title" ),
            int( widget.get_attribute( "-slot" ) )
        )


        # Page back as we prepare to transition to the keyboard
        self.page_back(1)


        # Fire an event with params
        self.fire_event(
            "show:game.save.keyboard",
            {
                "overwrite": "1",
                "title": save_title,
                "slot": save_slot
            }
        )

        # Return events
        return results


    # Show the save game keyboard (for entering save file title)
    def handle_show_game_save_keyboard_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Save game location on disk for the current universe
        path = universe.get_working_save_data_path()


        # Get a list of all previous saves
        files = os.listdir(path)



        # Default to no title
        title = ""


        # We'll save to the first unused slot
        counter = 1

        # Determine the first unused slot
        while ( ("manualsave%d" % counter) in files ):

            counter += 1


        # If this is an "overwrite" keyboard, we should fetch the slot number and
        # previously-specified save title.
        if ( int( params["overwrite"] ) == 1 ):

            # Grab title
            title = params["title"]

            # Grab slot
            counter = int( params["slot"] )


        # Fetch keyboard template
        template = self.fetch_xml_template("game.save.keyboard").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % (SCREEN_HEIGHT - PAUSE_MENU_Y) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@default": xml_encode( "%s" % title )
        })

        # Compile template
        root = template.compile_node_by_id("keyboard")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("save-game-keyboard")

        # We need to track a couple of params in the keyboard
        widget.set_attribute( "-save-type", "manual.new" )      # Create a custom save
        widget.set_attribute( "-save-slot", "%d" % counter )    # Save to folderN
        widget.set_attribute( "-quicksave", "%d" % 0 )          # Not a quicksave


        # Position the widget to appear from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Then it will slide into default position
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the save game keyboard
    def handle_hide_game_save_keyboard_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Grab widget
        widget = self.get_widget_by_id("save-game-keyboard")

        # Slide and hide
        widget.slide(DIR_DOWN, amount = SCREEN_HEIGHT)
        widget.hide(
            on_complete = "back"
        )

        # Return events
        return results


    # Check keyboard submission; validate input before proceeding.
    def handle_submit_game_save_keyboard_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the save controller
        save_controller = control_center.get_save_controller()


        # Get a handle to the keyboard
        keyboard = self.get_widget_by_id("save-game-keyboard")


        # What title did the user enter?
        title = keyboard.get_value().strip() # Trim excess whitespace


        # As long as the title validates...
        if ( save_controller.validate_save_title(title) ):

            # Hide the keyboard, calling for a .commit when it finally disappears.
            # (We'll still be able to reference the keyboard to get save param data.)
            keyboard.hide(
                on_complete = "commit:game.save.save"
            )

        # Elsewise, we'll give them an error message...
        else:

            # Fetch the "save game error" template
            template = self.fetch_xml_template("game.save.error").add_parameters({
                "@title": xml_encode( title ),
                "@error": xml_encode( save_controller.get_reason_for_save_title_invalidation(title) )
            })

            # Compile template
            root = template.compile_node_by_id("alert")

            # Convert to widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("new-save-error")


            # Add overlay
            self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Show the "are you sure you want to overwrite this save?" dialog page
    def handle_show_game_save_overwrite_confirm_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the save controller
        save_controller = control_center.get_save_controller()


        # Which version will we want?  Default to custom save...
        version = "custom"

        # Quicksave instead?
        if ( params["quicksave"] == "1" ):

            version = "quicksave"

            # Switch to ":new" version if the player
            # hasn't used this slot yet...
            if (
                get_file_modified_time(
                    save_controller.get_path_to_slot(universe, int( params["slot"] ), quicksave = (params["quicksave"] == "1"), autosave = False) # Can't overwrite an autosave from GUI, so ignore...
                ) == 0
            ):

                version = "quicksave:new"


        # Fetch the "are you sure? template
        template = self.fetch_xml_template("game.save.overwrite.confirm", version = version).add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_PROMPT_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@title": xml_encode( params["title"] ),
            "@quicksave": xml_encode( params["quicksave"] ),
            "@slot": xml_encode( params["slot"] ),
            "@time-since-last-save": xml_encode(
                format_timedelta(
                    int(time.time()),
                    get_file_modified_time(
                        save_controller.get_path_to_slot(universe, int( params["slot"] ), quicksave = (params["quicksave"] == "1"), autosave = False) # Can't overwrite an autosave from GUI, so ignore...
                    )
                )
            )
        })

        # Compile template
        root = template.compile_node_by_id("save.confirm-overwrite")

        # Create alert
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("prompt-confirm-overwrite")


        # Lastly, add the overlay!
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Handle confirmation of a game save overwrite.  For quicksaves, we'll immediately overwrite the save.
    # For manual saves, we'll show the keyboard so that they might change the save game title if they want.
    def handle_confirm_game_save_overwrite_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the confirmation overlay
        widget = self.get_widget_by_id("prompt-confirm-overwrite")


        # Is this a quicksave?  If so, we don't need a keyboard; we'll just commit the overwrite...
        if ( params["quicksave"] == "1" ):

            # We need to track a couple of params in the fading confirmation alert widget
            widget.set_attribute( "-save-type", "manual.new" )             # Create a custom save
            widget.set_attribute( "-save-slot", "%s" % params["slot"] )    # Save to folderN
            widget.set_attribute( "-quicksave", "%d" % 1 )                 # It is a quicksave

            # Hide alert
            widget.hide(
                on_complete = "commit:game.save.save"
            )


        # No; it's a custom save, so we'll show a keyboard for them to enter the new title (or to reuse the previous title)
        else:

            # Track params in fading widget
            widget.set_attribute( "-title", params["title"] )
            widget.set_attribute( "-slot", "%s" % params["slot"] )

            # Hide alert, call for keyboard when done
            widget.hide(
                on_complete = "transition:save-game-keyboard"
            )

        # Return events
        return results


    # Commit a game save.  Save to disk.
    def handle_commit_game_save_save_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the save controller
        save_controller = control_center.get_save_controller()


        # We need a handle to the widget that called for this overwrite, whether it was the
        # "are you sure?" page (on a quicksave) or the "keyboard" page (for overwriting a custom-titled save).
        # That widget is tracking the parameters for this save job.
        widget = self.get_active_page()#get_widget_by_id("prompt-confirm-overwrite")

        # Grab save params
        (save_title, save_type, save_slot, quicksave) = (
            "",
            widget.get_attribute("-save-type"),                 # Unused?
            int( widget.get_attribute("-save-slot") ),
            ( int( widget.get_attribute("-quicksave") ) == 1 )
        )

        # Check for save title if it's not a quicksave
        if (not quicksave):

            save_title = widget.get_value()


        # Now that we have extracted the param data from the (now hidden) previous (and now vanished) page,
        # we can page back.  (We'll give the user a newsfeeder item confirmation when we're done.)
        self.page_back(1)


        # Quicksaves save to the specific slot...
        if (quicksave):

            # Construct metadata for this save...
            xml = save_controller.construct_metadata_with_title("Quicksave %d" % save_slot, universe)

            # Save game, quicksave
            save_controller.save_to_slot(save_slot, universe, quicksave = True, autosave = False, metadata = xml)


            # Post a newsfeeder item confirming save
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_GAME_SAVE_COMPLETE,
                "title": control_center.get_localization_controller().get_label("save-complete:title"),
                "content": control_center.get_localization_controller().get_label("quicksave-n-complete:message", { "@n": save_slot })
            })

        # Manual saves may either create a new slot or overwrite an existing slot...
        else:

            # Construct metadata for this save...
            xml = save_controller.construct_metadata_with_title(save_title, universe)

            # Save game!
            save_controller.save_to_slot(save_slot, universe, quicksave = False, autosave = False, metadata = xml)


            # Post a newsfeeder item confirming save
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_GAME_SAVE_COMPLETE,
                "title": control_center.get_localization_controller().get_label("save-complete:title"),
                "content": control_center.get_localization_controller().get_label("customsave-n-complete:message", { "@n": save_title.lower() })
            })


        # Rebuild the pause menus to reflect the new data...
        #self.refresh_pages(user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, curtailed_count = 0)
        self.refresh_pages(control_center, universe, curtailed_count = 0)


    # Show the "load game" screen
    def handle_show_game_load_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the save controller
        save_controller = control_center.get_save_controller()


        """ Find custom saves """
        # Build a list of any manual save before we create and populate the template...
        path = universe.get_working_save_data_path()

        # List files
        files = os.listdir(path)

        # Track which folders are manual saves...
        matching_files = []

        for each in files:

            # I only care about the manual saves...
            prefix = "manualsave"

            if (each.startswith(prefix)):

                matching_files.append( os.path.join(path, each) )


        # Sort matching files, newest-to-oldest...
        matching_files = sort_files_by_date(matching_files)


        """ Build load directory """
        # Get the path to last checkpoint
        path = os.path.join( universe.get_working_save_data_path(), "autosave1" )

        # Search for metadata related to last autosave
        metadata = save_controller.fetch_metadata_from_folder(path, universe)


        # Fetch the template for the load game menu
        template = self.fetch_xml_template("game.load").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@quicksave-slot-count": xml_encode( "%d" % MAX_QUICKSAVE_SLOTS ),
            "@manualsave-slot-count": xml_encode( "%d" % len(matching_files) ),
            "@character-level": xml_encode( "%s" % metadata["character-level"] ),
            "@gold-collected": xml_encode( "%s" % metadata["gold-recovered"] )
        })

        # Compile the root menu
        root = template.compile_node_by_id("load-game")


        """ Inject quicksaves """
        # Now process any quicksave slot...
        zebra = False

        # Easy lookup
        template_versions_by_zebra = {
            False: "normal",
            True:  "zebra"
        }

        # Loop "n" quicksave slots
        for slot in range(1, MAX_QUICKSAVE_SLOTS + 1):

            # Get the path to potential autosaves for this universe
            path = os.path.join( universe.get_working_save_data_path(), "quicksave%d" % slot )

            # Quickly, let's try to fetch this save's metadata...
            metadata = save_controller.fetch_metadata_from_folder(path, universe)


            # Fetch template for quicksave iter
            template = self.fetch_xml_template( "game.load.quicksave", version = template_versions_by_zebra[zebra] ).add_parameters({
                "@title": xml_encode( metadata["title"] ),
                "@date": xml_encode( metadata["last-modified-date"] ),
                "@quicksave-slot": xml_encode( "%d" % slot ),
                "@slot": xml_encode( "%d" % slot ),
                "@thumbnail": xml_encode( os.path.join(path, "thumb.png") ),
                "@trailing-margin": xml_encode( "0" ),
                "@xtrailing-margin": xml_encode( "%d" % ( max(0, (1 + slot - MAX_AUTOSAVE_SLOTS) * 10) ) ),
                "@character-level": xml_encode( "%s" % metadata["character-level"] ),
                "@gold-collected": xml_encode( "%s" % metadata["gold-recovered"] ) # Inconsistent keys, collected -vs- recovered...
            })

            # Compile the node for this iter
            node = template.compile_node_by_id("file")

            # Inject the node into the appropriate root...
            root.find_node_by_id("ext.quicksaves").add_node(node)


            # Toggle zebra
            zebra = (not zebra)


        """ Inject custom saves """
        # Now process any matching file...
        zebra = False

        # Easy lookup
        template_versions_by_zebra = {
            False: "normal",
            True:  "zebra"
        }

        # Loop files
        for each in matching_files:

            # Get the path to potential manual saves for this universe
            path = universe.get_working_save_data_path()

            # I only care about the manual saves...
            prefix = os.path.join(path, "manualsave")

            # Quickly, let's try to fetch this save's metadata...
            metadata = save_controller.fetch_metadata_from_folder(each, universe)


            # Fetch manualsave template
            template = self.fetch_xml_template( "game.load.manualsave", version = template_versions_by_zebra[zebra] ).add_parameters({
                "@title": xml_encode( metadata["title"] ),
                "@date": xml_encode( metadata["last-modified-date"] ),
                "@manualsave-slot": xml_encode( each[len(prefix) : len(each)] ),
                "@slot": xml_encode( each[len(prefix) : len(each)] ),
                "@thumbnail": xml_encode( os.path.join(each, "thumb.png") ),
                "@character-level": xml_encode( "%s" % metadata["character-level"] ),
                "@gold-collected": xml_encode( "%s" % metadata["gold-recovered"] ) # Inconsistent keys, collected -vs- recovered...
            })

            # Compile this iter's node
            node = template.compile_node_by_id("file")

            # Inject into the appropriate group
            root.find_node_by_id("ext.manualsaves").add_node(node)


            # Toggle zebra
            zebra = (not zebra)


        """ Finish """
        # Create the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("load-game")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Officially add the overlay...
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show the load game confirmation page
    def handle_show_game_load_confirm_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Determine which type of slot we're loading...
        (is_autosave, is_quicksave) = (
            (params["autosave"] == "1"),
            (params["quicksave"] == "1")
        )

        # Prepare to calculate path / title / template version
        (path, title, version) = (
            "",
            "",
            ""
        )

        # Which save slot?
        slot = int( params["slot"] )


        # Determine appropriate path...
        if (is_autosave):

            (path, title, version) = (
                os.path.join( universe.get_working_save_data_path(), "autosave%d" % slot ),
                "Last Checkpoint",#"Autosave Slot %d" % slot
                "autosave"
            )

        elif (is_quicksave):

            (path, title, version) = (
                os.path.join( universe.get_working_save_data_path(), "quicksave%d" % slot ),
                "Quicksave %d" % slot,
                "quicksave"
            )

        else:

            (path, title, version) = (
                os.path.join( universe.get_working_save_data_path(), "manualsave%d" % slot ),
                "%s" % params["title"],
                "manualsave"
            )


        # Validate that we can find save data there...
        if (os.path.exists(path)):

            # Fetch the appropriate confirmation template
            template = self.fetch_xml_template( "game.load.confirm", version = version ).add_parameters({
                "@width": xml_encode( "%d" % PAUSE_MENU_PROMPT_WIDTH ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@path": xml_encode( path ),
                "@slot": xml_encode( "%d" % slot ),
                "@title": xml_encode( title )
            })

            # Compile template
            root = template.compile_node_by_id("load.confirm")

            # Create alert
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("prompt-confirm-load-game")


            # Lastly, add the overlay!
            self.add_widget_via_event(widget, event, exclusive = False)

        # Display a "no data found" message
        else:

            # Fetch the necessary template
            template = self.fetch_xml_template("game.load.na").add_parameters({
                "width": xml_encode( "%d" % PAUSE_MENU_PROMPT_WIDTH ),
                "height": xml_encode( "%d" % SCREEN_HEIGHT )
            })

            # Compile template
            root = template.compile_node_by_id("load.na")

            # Create the wideget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("prompt-confirm-no-load-game-data")


            # Lastly, add the overlay!
            self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Handle a "load game" event (confirmed)
    def handle_commit_game_load_load_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the window controller
        window_controller = control_center.get_window_controller()


        # The active page needs to remember the path that we're going to load from, because
        # we're going to wait for an app-level fade before really loading.
        self.get_active_page().set_attribute( "-path", "%s" % params["path"] )


        # Hook into the window controller
        window_controller.hook(self)

        # App-level fade, followed by a forwarded load game event
        window_controller.fade_out(
            on_complete = "fwd.transparent:game.load.load"
        )
        #    lambda q = self.event_queue, path = params["path"]: q.add(
        #        action = "fwd.transparent:game.load.load",
        #        params = {
        #            "path": path
        #        }
        #    )
        #)

        # Return events
        return results


    # Finalize the "load game" event (fade has ended)
    def handle_transparent_game_load_load_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the save controller;
        save_controller = control_center.get_save_controller()

        # and the splash controller.
        splash_controller = control_center.get_splash_controller()


        # Unhook from the window controller
        window_controller.unhook(self)

        # The current page is tracking the path that we're going to load from...
        path = self.get_active_page().get_attribute("-path")


        # Load the saved game from disk...
        save_controller.load_from_folder(path, control_center, universe)


        log( "UI Load Game:  ", universe.get_session_variable("app.active-map-name").get_value() )
        log( "Path:  ", path )


        #f = open( os.path.join("debug", "2.xml"), "w" )
        #for v in universe.session:
        #    f.write("%s = '%s'\n" % (v, universe.session[v]))
        #f.close()

        # Also dismiss the splash controller entirely
        splash_controller.abort()


        # Now transition the universe to the currently active map (for the new save game file).
        # The universe will, by default, place the player entity at the position it occupied
        # most recently in the session (when we saved), because we do not specify a "to" waypoint.
        universe.transition_to_map(
            universe.get_session_variable("app.active-map-name").get_value(),
            control_center = control_center,
            save_memory = False
        )

        # Post a newsfeeder item confirming load
        window_controller.get_newsfeeder().post({
            "type": NEWS_GAME_SAVE_COMPLETE,
            "title": control_center.get_localization_controller().get_label("load-complete:title"),
            "content": control_center.get_localization_controller().get_label("load-complete:message")
        })


        # App-level fade back in to show the game again
        window_controller.fade_in()

        # Resume gameplay from the save we just loaded
        universe.unpause()


        # Fire kill event
        self.fire_event("kill")


        # Return events
        return results


    # Show the worldmap
    def handle_show_game_worldmap_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch world map menu template
        template = self.fetch_xml_template("game.worldmap").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@view-title": xml_encode( WORLDMAP_VIEW_LABELS[ universe.get_session_variable("core.worldmap.view").get_value() ] ),
            "@default-view": xml_encode( universe.get_session_variable("core.worldmap.view").get_value() ),
            "@default-zoom": xml_encode( universe.get_session_variable("core.worldmap.zoom").get_value() ),
        })

        # Compile template
        root = template.compile_node_by_id("directory")


        # Before converting the node to the final widget, we might want to sneak in a
        # "disabled" attribute on the travel option.
        if ( universe.get_session_variable("core.minimap.can-travel").get_value() == "no" ):

            # We're adding this into the XML as an attribute
            root.find_node_by_id("btn-travel").set_attributes({
                "disabled": "1"
            })


        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("worldmap")


        # I want to center the Worldmap widget on the player's current location in the overworld
        #widget.find_widget_by_id("map").center_on_map_by_name(
        #    universe.get_active_map().get_name()
        #)

        logn( "pause-menu worldmap", "center on (%d, %d)" % (universe.get_map_data( universe.get_active_map().get_name() ).x, universe.get_map_data( universe.get_active_map().get_name() ).y) )


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # "Step into" the worldmap options rowmenu (because it's its own RowMenu widget, not a continuation of the overall directory like many menu screens)
    # position should be "beginning" or "end."
    def handle_show_game_worldmap_step_in_event(self, event, control_center, universe, position):

        # Track local results
        results = EventQueue()


        # Get the directory
        directory = self.get_widget_by_id("worldmap")

        # Configure the directory's tunnel target to point to the hpane that holds the options RowMenu widget
        directory.configure({
            "tunnel-target-id": "tunnel"
        })


        # Set cursor on the directory to beginning or end
        if (position == "beginning"):

            # First option
            directory.find_widget_by_id("options").set_cursor_at_beginning()

        elif (position == "end"):

            # Last option
            directory.find_widget_by_id("options").set_cursor_at_end()


        logn( "pause-menu", "cursor position:  ", position )


        # Return events
        return results


    # Step out of the worldmap options RowMenu widget, returning focus to the directory (which is only the back button)
    def handle_show_game_worldmap_step_out_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()


        # Get the directory
        directory = self.get_widget_by_id("worldmap")

        # Remove the tunnel target id, allowing the directory RowMenu to regain focus
        directory.configure({
            "tunnel-target-id": ""
        })


        # Return events
        return results


    # Show the views we can apply to the worldmap
    def handle_show_game_worldmap_views_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the views template
        template = self.fetch_xml_template("game.worldmap.views").add_parameters({
            "@x": xml_encode( "%d" % ( int(PAUSE_MENU_WIDTH / 2) - int(480 / 2) ) ), # hard-coded
            "@width": xml_encode( "%d" % 480 ), # hard-coded
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Build template
        root = template.compile_node_by_id("views")

        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("worldmap-views")

        # Add new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Set the active view for the game worldmap
    def handle_commit_game_worldmap_views_set_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the row menu (directory)
        row_menu = self.get_widget_by_id("worldmap")

        # Fetch the item wrapper, then its widget container, then the darned map...
        worldmap = row_menu.find_widget_by_id("map")

        # Validate
        if (worldmap):

            # Configure the new view
            worldmap.configure({
                "view": params["view"]
            })

        # Track view via session
        universe.set_session_variable( "core.worldmap.view", params["view"] )

        # Refresh the pages
        self.refresh_pages(control_center, universe, curtailed_count = 1)

        # Return events
        return results


    # Use the worldmap (e.g. zoom, pan, etc.)
    def handle_commit_game_worldmap_use_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the row menu (directory)
        row_menu = self.get_widget_by_id("worldmap")

        # Fetch the item wrapper, then its container (wrapper), then the worldmap itself
        worldmap = row_menu.find_widget_by_id("map")


        # Make the directory tunnel its input to the worldmap
        row_menu.configure({
            "tunnel-target-id": "map-wrapper"
        })

        # Set input mode on the worldmap, plus any other relevant param.
        worldmap.configure({
            "input-mode": params["mode"],
            "selected-map": universe.get_session_variable("core.last-safe-zone.map").get_value() # This will only directly apply when using the worldmap's "travel" mode
        })

        # Return events
        return results


    # Show the "are you sure you want to travel?" confirmation
    def handle_show_game_worldmap_travel_confirm_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the page that contains the worldmap directory (map and buttons)
        page = self.get_widget_by_id("worldmap")

        # Now fetch the worldmap widget within that page
        widget = page.find_widget_by_id("map")


        # Get the worldmap's actively selected map name
        selected_map_name = widget.selected_map_name

        # Find map data for that map
        map_data = universe.get_map_data(selected_map_name)


        # Validate, I guess
        if (map_data):

            # Fetch the confirmation template
            template = self.fetch_xml_template("gamemenu.worldmap.travel.confirm").add_parameters({
                "@x": xml_encode( "%d" % ( int(PAUSE_MENU_WIDTH / 2) - int(PAUSE_MENU_WIDTH / 2) ) ),
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@map-name": xml_encode( "%s" % map_data.get_name() ),
                "@map-title": xml_encode( "%s" % map_data.get_title() )
            })

            # Build template
            root = template.compile_node_by_id("travel.confirm")

            # Create widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("worldmap-travel-confirm")

            # Add new page
            self.add_widget_via_event(widget, event, exclusive = False)


        # Return events
        return results


    # Travel to a town on the worldmap
    def handle_commit_game_worldmap_travel_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()


        # The active page needs to remember the name of the map that we're going to travel to, because
        # we're going to wait for an app-level fade before finishing.
        self.get_active_page().set_attribute( "-map-name", "%s" % params["map-name"] )


        # Hook into the window controller
        window_controller.hook(self)

        # App-level fade, followed by a forwarded "finish travel" event
        window_controller.fade_out(
            on_complete = "fwd.finish:game.worldmap.travel"
        )

        # Return events
        return results


    # Receive forwarded event from the window controller, indicating that the app-level fade has completed
    # and we should commit the worldmap travel event now.
    def handle_fwd_finish_game_worldmap_travel_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the splash controller.
        splash_controller = control_center.get_splash_controller()


        # Unhook from the window controller
        window_controller.unhook(self)

        # The current page is tracking the name of the map we want to go to
        name = self.get_active_page().get_attribute("-map-name")


        # Transition to the given map.  Save the memory state of the current map, too.
        universe.transition_to_map(
            name,
            waypoint_to = "spawn", # The fast-travel map destination should have a trigger named "spawn" on it that indicates where the player should spawn after a fast-travel.
            control_center = control_center,
            save_memory = True
        )


        # Get player entity
        player = universe.get_active_map().get_entity_by_name("player1")

        # Validate (though if we have no player after this, that's not good either...)
        if (player):

            # Remember the player's new position as they enter the new map, for autosave purposes
            universe.set_session_variable( "core.player1.x", "%d" % player.get_x() )
            universe.set_session_variable( "core.player1.y", "%d" % player.get_y() )


        # App-level fade back in to show the game again
        window_controller.fade_in()

        # Resume gameplay from the save we just loaded
        universe.unpause()


        # Having arrived at the new map, let's directly feed a new autosave event
        # to the Universe object.  UI events don't return to the Universe object, so we have to do this directly.
        universe.handle_event(
            EventQueueIter("autosave"),
            control_center,
            universe
        )


        # Fire a kill event to dismiss the entire pause menu widget
        self.fire_event("kill")

        """


        # Load the saved game from disk...
        save_controller.load_from_folder(path, control_center, universe)


        log( "UI Load Game:  ", universe.get_session_variable("app.active-map-name").get_value() )
        log( "Path:  ", path )


        #f = open( os.path.join("debug", "2.xml"), "w" )
        #for v in universe.session:
        #    f.write("%s = '%s'\n" % (v, universe.session[v]))
        #f.close()

        # Also dismiss the splash controller entirely
        splash_controller.abort()


        # Now transition the universe to the currently active map (for the new save game file).
        # The universe will, by default, place the player entity at the position it occupied
        # most recently in the session (when we saved), because we do not specify a "to" waypoint.
        universe.transition_to_map(
            universe.get_session_variable("app.active-map-name").get_value(),
            control_center = control_center,
            save_memory = False
        )

        # Post a newsfeeder item confirming load
        window_controller.get_newsfeeder().post({
            "type": NEWS_GAME_SAVE_COMPLETE,
            "title": control_center.get_localization_controller().get_label("load-complete:title"),
            "content": control_center.get_localization_controller().get_label("load-complete:message")
        })


        # App-level fade back in to show the game again
        window_controller.fade_in()

        # Resume gameplay from the save we just loaded
        universe.unpause()


        # Fire kill event
        self.fire_event("kill")
        """


        # Return events
        return results


    # Yield from the worldmap; stop using it, resume use of the worldmap page itself
    def handle_commit_game_worldmap_yield_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the row menu (directory)
        row_menu = self.get_widget_by_id("worldmap")

        # Remove tunnel target from the rowmenu
        row_menu.configure({
            "tunnel-target-id": ""
        })


        # Focus on the RowMenu to make the buttons light up again
        row_menu.focus()


        # Return events
        return results


    # show the "my reputation" screen
    def handle_show_inventories_reputation_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()


        # Fetch achievement directory template
        template = self.fetch_xml_template("misc.reputation").add_parameters({
            "@x": xml_encode( "%d" % 0 ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Create root node
        root = template.compile_node_by_id("menu")


        # Prepare an empty list of paragraphs
        paragraphs = []


        # Get all source data for creating the reputation screen
        data = XMLParser().create_node_from_file( os.path.join(UNIVERSES_PATH, universe.get_name(), "reputation.xml") )

        # Validate
        if (data):

            # If we've only played for a short whlie, then we'll
            # use the "early" data rules.
            if ( int( universe.get_session_variable("core.time.played").get_value() ) < REPUTATION_READY ):

                # Step into the "early" data
                data = data.find_node_by_tag("early")

                # Validate data node exists
                if (data):

                    # Find overview node
                    ref = data.find_node_by_tag("overview")

                    # Validate
                    if (ref):

                        # Add overview
                        paragraphs.append(ref.innerText)


                    # Calculate the percentage of NPCs killed
                    percent = int( float( universe.get_session_variable("npc.count.dead").get_value() ) / float( universe.get_session_variable("npc.count.total").get_value() ) * 100.0 )
                    tag = None

                    # None?
                    if (percent == 0):
                        tag = "none"

                    # A few?
                    elif (percent < 10):
                        tag = "some"

                    # Lots?
                    elif (percent < 100):
                        tag = "lots"

                    # All???
                    else:
                        tag = "all"


                    # Find appropriate npc kill reputation data
                    ref = data.find_node_by_tag("npc-kills")
                    if (ref):

                        # Validation of desired tag
                        ref = ref.find_node_by_tag(tag)
                        if (ref):

                            # Add paragraph
                            paragraphs.append(ref.innerText)


                    # Count number of enemies killed so far
                    kills = int( universe.get_session_variable("stats.enemies-killed").get_value() )
                    tag = None

                    # None?
                    if (kills == 0):
                        tag = "none"

                    # A few?
                    elif (kills <= 10):
                        tag = "some"

                    # Lots?
                    else:
                        tag = "lots"


                    # Find appropriate enemy kill reputation data
                    ref = data.find_node_by_tag("enemy-kills")
                    if (ref):

                        # Validation of desired tag
                        ref = ref.find_node_by_tag(tag)
                        if (ref):

                            # Add paragraph
                            paragraphs.append(ref.innerText)


                    # Calculate the number of levels completed, along with the number possible
                    (a, b) = (
                        len( [o for o in universe.get_map_data_by_class("overworld") if o.is_map_completed() == True] ),
                        len( universe.get_map_data_by_class("overworld") )
                    )

                    # Calculate percentage
                    percent = int( float(a) / float(b) * 100.0 )
                    tag = None

                    # None?
                    if (a == 0):
                        tag = "none"

                    # One?
                    elif (a == 1):
                        tag = "some"

                    # Many?
                    elif (a < b):
                        tag = "lots"

                    # All?
                    else:
                        tag = "all"


                    # Find appropriate levels complete reputation data
                    ref = data.find_node_by_tag("levels-complete")
                    if (ref):

                        # Validation of desired tag
                        ref = ref.find_node_by_tag(tag)
                        if (ref):

                            # Add paragraph
                            paragraphs.append(ref.innerText)


            # If we've played for a certain length of time, we'll use the "late" data
            else:

                # Step into the "late" data
                data = data.find_node_by_tag("late")

                # Validate data node exists
                if (data):

                    # Find overview node
                    ref = data.find_node_by_tag("overview")

                    # Validate
                    if (ref):

                        # Add overview
                        paragraphs.append(ref.innerText)


                    # Calculate the percentage of NPCs killed
                    percent = int( float( universe.get_session_variable("npc.count.dead").get_value() ) / float( universe.get_session_variable("npc.count.total").get_value() ) * 100.0 )
                    tag = None

                    # None?
                    if (percent == 0):
                        tag = "none"

                    # A few?
                    elif (percent < 30):
                        tag = "some"

                    # Lots?
                    elif (percent < 100):
                        tag = "lots"

                    # All???
                    else:
                        tag = "all"


                    # Find appropriate npc kill reputation data
                    ref = data.find_node_by_tag("npc-kills")
                    if (ref):

                        # Validation of desired tag
                        ref = ref.find_node_by_tag(tag)
                        if (ref):

                            # Add paragraph
                            paragraphs.append(ref.innerText)


                    # Count number of enemies killed so far
                    kills = int( universe.get_session_variable("stats.enemies-killed").get_value() )
                    tag = None

                    # None?
                    if (kills == 0):
                        tag = "none"

                    # A few?
                    elif (kills <= 50):
                        tag = "some"

                    # Lots?
                    else:
                        tag = "lots"


                    # Find appropriate enemy kill reputation data
                    ref = data.find_node_by_tag("enemy-kills")
                    if (ref):

                        # Validation of desired tag
                        ref = ref.find_node_by_tag(tag)
                        if (ref):

                            # Add paragraph
                            paragraphs.append(ref.innerText)


                    # Calculate the number of levels completed, along with the number possible
                    (a, b) = (
                        len( [o for o in universe.get_map_data_by_class("overworld") if o.is_map_completed() == True] ),
                        len( universe.get_map_data_by_class("overworld") )
                    )

                    # Calculate percentage
                    percent = int( float(a) / float(b) * 100.0 )
                    tag = None

                    # None?
                    if (percent == 0):
                        tag = "none"

                    # A few?
                    elif (percent < 20):
                        tag = "some"

                    # Many?
                    elif (percent < 100):
                        tag = "lots"

                    # All?
                    else:
                        tag = "all"


                    # Find appropriate levels complete reputation data
                    ref = data.find_node_by_tag("levels-complete")
                    if (ref):

                        # Validation of desired tag
                        ref = ref.find_node_by_tag(tag)
                        if (ref):

                            # Add paragraph
                            paragraphs.append(ref.innerText)


        # Loop through paragraphs
        for p in paragraphs:

            # Fetch template
            template = self.fetch_xml_template("misc.reputation.insert").add_parameters({
                "@data": xml_encode(
                    universe.translate_session_variable_references(
                        control_center.get_localization_controller().translate("%s" % p),
                        control_center = None
                    )
                )
            })

            # Add paragraph
            root.find_node_by_id("ext.paragraphs").add_node(
                template.compile_node_by_id("insert")
            )


        # Convert node to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        # Set new widget's id
        widget.set_id("misc-reputation")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Handle a "scroll reputation up" event
    def handle_reputation_scroll_up_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()


        # Get a handle to the (disabled) row menu
        widget = self.get_widget_by_id("misc-reputation").find_widget_by_id("scroller")

        # Validate
        if (widget):

            #pass
            widget.autoscroll_n_steps(-1)


        # Return events
        return results


    # Handle a "scroll reputation down" event
    def handle_reputation_scroll_down_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()


        # Get a handle to the (disabled) row menu
        widget = self.get_widget_by_id("misc-reputation").find_widget_by_id("scroller")

        # Validate
        if (widget):

            #pass
            widget.autoscroll_n_steps(1)


        # Return events
        return results


    # Show the player's item inventory and allow them to manage it
    def handle_show_inventories_inventory_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        """ Build base directory """
        # Let's fetch any item the player is wearing...
        equipped_items = universe.get_equipped_items()

        # Every item we've acquired so far...
        acquired_items = universe.get_acquired_items()#_names(sorting_method = "alpha", descending = False)


        # Fetch template
        template = self.fetch_xml_template("inventory.directory").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@slots": xml_encode( universe.get_session_variable("core.player1.inventory-size").get_value() ),
            "@count": xml_encode( "%d" % len(acquired_items) ),
            "@test": "TEST"
        })

        # Compile root
        root = template.compile_node_by_id("directory")


        # Zebra striping for equippable item slots...
        zebra = False

        # Loop through each available slot...
        for slot in range(0, int( universe.get_session_variable("core.player1.inventory-size").get_value() )):

            # Anything equipped in this slot?
            if ( len(equipped_items) > slot ):

                # Version
                version = "occupied"

                # Zebra?
                if (zebra):

                    version = "%s:zebra" % version


                # Fetch appropriate template
                template = self.fetch_xml_template( "inventory.equipped.insert", version = version ).add_parameters({
                    "@slot": xml_encode( "%d" % slot ),
                    "@item-name": xml_encode( equipped_items[slot].name ),
                    "@item-title": xml_encode( equipped_items[slot].title ),
                    "@item-summary": xml_encode( equipped_items[slot].get_description() ),
                    "@count": xml_encode( "%d" % len(acquired_items) )
                })

                # Compile template
                node = template.compile_node_by_id("insert")

                # Inject the new node into the appropriate root...
                root.find_node_by_id("ext.equipped-items").add_node(node)

            # No; we'll use an "empty slot" template instead...
            else:

                # Version
                version = "empty"

                # Zebra?
                if (zebra):

                    version = "%s:zebra" % version


                # Get template
                template = self.fetch_xml_template( "inventory.equipped.insert", version = version ).add_parameters({
                    "@slot": xml_encode( "%d" % slot ),
                    "@count": xml_encode( "%d" % len(acquired_items) )
                })

                # Compile
                node = template.compile_node_by_id("insert")


                # Inject the new node into the appropriate root...
                root.find_node_by_id("ext.equipped-items").add_node(node)

            # Strip zebra!
            zebra = (not zebra)


        # Zebra tracking as we prepare to render all items the player has acquired
        zebra = False

        # Append markup for each item...
        for item in acquired_items:

            # Do we have this item equipped already?  This will determine the template we use...
            version = "not-equipped"

            # Already equipped, huh?
            if ( universe.is_item_equipped(item.name) ):

                version = "equipped"

            # Not equipped, but no slot free?  Offer a "replace existing item" type of template...
            elif ( len( universe.get_equipped_items() ) >= int( universe.get_session_variable("core.player1.inventory-size").get_value() ) ):

                version = "not-equipped:no-free-slot"


            # Zebra version?
            if (zebra):

                version = "%s:zebra" % version


            # Fetch the appropriate template / version
            template = self.fetch_xml_template( "inventory.myitems.insert", version = version ).add_parameters({
                "@item-name": xml_encode( item.name ),
                "@item-title": xml_encode( item.title ),
                "@item-summary": xml_encode( item.get_description() )
            })

            # Compile template
            node = template.compile_node_by_id("insert")

            # Inject the new node into the appropriate root...
            root.find_node_by_id("ext.my-items").add_node(node)


            # Stripe the zebra
            zebra = (not zebra)


        # Create the directory widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("inventory-home")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show inventory item options for a currently equipped item
    def handle_show_inventories_inventory_equipped_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the default text renderer
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


        """ Item object stuff """
        # Get a reference to the item in question, if we have one in this slot...
        item = universe.get_acquired_item_by_name( params["item-name"] )

        # Let's fetch any item the player is wearing, just so we can calculate the number of free slots available...
        equipped_items = universe.get_equipped_items()


        log2( item.save_state().compile_xml_string() )


        """ Build options menu """
        # Fetch template
        template = self.fetch_xml_template( "inventory.equipped.insert.options", version = "occupied" ).add_parameters({
            "@x": xml_encode( "%d" % ( 0 if ( params["side"] == "left" ) else (20 + int(PAUSE_MENU_WIDTH / 2)) ) ), # kinda hacky!
            "@y": xml_encode( "0" ),#"%d" % widget_stack.get_y_offset_by_widget_id("content", text_renderer) )
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@side": xml_encode( params["side"] ),
            "@item-name": xml_encode( item.name ),
            "@item-title": xml_encode( item.title ),
            "@slots-free": xml_encode( "%d" % len(equipped_items) ),
            "@slots-total": xml_encode( universe.get_session_variable("core.player1.inventory-size").get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("equipped.options")


        """ Add available upgrades """
        # Count the number of remaining upgrades for this item (typically just 1)
        remaining_upgrades = item.count_remaining_upgrades()


        # If we can still upgrade this item, then let's add each available upgrade as an option...
        if (remaining_upgrades > 0):

            # Check how much money the player has
            money = int( universe.get_session_variable("core.gold.wallet").get_value() )

            # Loop through each available upgrade
            for upgrade in item.get_available_upgrades():

                # Which template will we want?
                template_version = ("affordable" if ( money >= upgrade.get_cost() ) else "unaffordable")

                # Fetch insert template
                template = self.fetch_xml_template( "inventory.item.upgrades.insert", version = template_version ).add_parameters({
                    "@side": xml_encode( params["side"] ),
                    "@opposite-side": xml_encode( "left" if (params["side"] == "right") else "right" ),
                    "@item-name": xml_encode( item.name ),
                    "@upgrade-name": xml_encode( upgrade.get_name() ),
                    "@upgrade-title": xml_encode( upgrade.get_title() ),
                    "@upgrade-cost": xml_encode( "%d" % upgrade.get_cost() ),
                    "@gold-needed": xml_encode( "%d" % ( upgrade.get_cost() - money ) ), # Only used for too-expensive template
                    "@upgrades-remaining": xml_encode( "%d" % remaining_upgrades ),
                    "@upgrades-remaining-pluralizer": xml_encode( ("s" if (remaining_upgrades > 1) else "") ) # Grammar technicality :)
                })

                # Compile template
                node = template.compile_node_by_id("insert")

                # Add it to the root's upgrades group
                root.find_node_by_id("ext.available-upgrades").add_node(node)

        # If we've upgraded the item all that we can, then we should display a "upgrades done" type of message
        else:

            # Fetch insert template
            template = self.fetch_xml_template( "inventory.item.upgrades.insert", version = "out-of-upgrades" ).add_parameters({
                "@item-name": xml_encode( item.name ) # Don't even need this...
            })

            # Compile template
            node = template.compile_node_by_id("insert")

            # Add it to the root's upgrades group
            root.find_node_by_id("ext.available-upgrades").add_node(node)


        # Create options widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)


        """ Slide effect """
        # Grab a reference to the inventory directory itself, so that we can slide it out of the way
        directory = self.get_widget_by_id("inventory-home")

        # Show options widget on the left?
        if ( params["side"] == "left" ):

            # slide the directory off to the righit
            directory.slide(DIR_RIGHT, amount = widget.get_width() + 20, delay = 0)


            # Position the options widget just to the left of the directory (mostly off-screen)
            widget.slide(DIR_LEFT, widget.get_width() + 20, animated = False)

            # Now have the options menu slide into view...
            widget.slide(None)

            # Remember which side we're on...
            widget.set_attribute("side", params["side"])


        # Okay, show it on the right, then...
        elif ( params["side"] == "right" ):

            # Slide the directory out of the way
            directory.slide(DIR_LEFT, amount = widget.get_width(), delay = 0)


            # Position the options widget just to the right of the directory
            widget.slide(DIR_RIGHT, amount = widget.get_width() + 20, animated = False)

            # Now, slide the options widget into view...
            widget.slide(None)#DIR_RIGHT, amount = directory.get_width() + 20 - widget.get_width(), delay = 0)

            # Remember which side we're on...
            widget.set_attribute("side", params["side"])



        widget.set_id("inventory-equipped-options")

        # Add the overlay
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the options page for a currently equipped item
    def handle_hide_inventories_inventory_equipped_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get the overlay representing the HPane with the options in it (equip, do nothing, etc.)
        widget = self.get_widget_by_id("inventory-equipped-options")

        # Get the inventory directory itself
        directory = self.get_widget_by_id("inventory-home")


        # Which side were we on?
        side = widget.get_attribute("side")

        if (side == "left"):

            # Hide and slide
            widget.hide()

            widget.slide(
                DIR_LEFT,
                amount = widget.get_width() + 20,
                on_complete = "previous-page"
            )

        elif (side == "right"):

            # Hide and slide
            widget.hide()

            # Slide the details off the screen...
            widget.slide(
                DIR_RIGHT,
                amount = directory.get_width() + 20,
                on_complete = "previous-page"#lambda widget, a = self, b = [], n = network_controller, c = universe, d = active_map, e = session, wd = widget_dispatcher, f = text_renderer, g = save_controller, p = {"do": "show-inventory.equipped:hide-options.cleanup"}: a.handle_selection(p, b, n, c, d, e, wd, f, g, widget)
            )

        # Return the directory to default slide (no slide)
        directory.slide(None)

        # Return events
        return results


    # Show the options menu for any given item that the player has acquired
    def handle_show_inventories_inventory_all_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the default text renderer
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


        """ Get item object """
        # Get a reference to the acquired item in question...
        item = universe.get_acquired_item_by_name( params["item-name"] )


        # Let's fetch any item the player is wearing (for statistical readouts)
        equipped_items = universe.get_equipped_items()


        """ Build options menu """
        # Fetch template
        template = self.fetch_xml_template( "inventory.myitems.insert.options", version = params["template-version"] ).add_parameters({
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ), # hard-coded
            "@x": xml_encode( "%d" % ( 0 if ( params["side"] == "left" ) else (20 + int(PAUSE_MENU_WIDTH / 2)) ) ), # somewhat hacky still!
            "@y": xml_encode( "0" ),#"%d" % widget_stack.get_y_offset_by_widget_id("content", text_renderer) )
            "@side": xml_encode( params["side"] ),
            "@item-name": xml_encode( item.name ),
            "@item-title": xml_encode( item.title ),
            "@slots-free": xml_encode( "%d" % len(equipped_items) ),
            "@slots-total": xml_encode( universe.get_session_variable("core.player1.inventory-size").get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("my-items.options")


        """ Add available upgrades """
        # Count the number of remaining upgrades for this item (typically just 1)
        remaining_upgrades = item.count_remaining_upgrades()


        # If we can still upgrade this item, then let's add each available upgrade as an option...
        if (remaining_upgrades > 0):

            # Check how much money the player has
            money = int( universe.get_session_variable("core.gold.wallet").get_value() )

            # Loop through each available upgrade
            for upgrade in item.get_available_upgrades():

                # Which template will we want?
                template_version = ("affordable" if ( money >= upgrade.get_cost() ) else "unaffordable")

                # Fetch insert template
                template = self.fetch_xml_template( "inventory.item.upgrades.insert", version = template_version ).add_parameters({
                    "@side": xml_encode( params["side"] ),
                    "@opposite-side": xml_encode( "left" if (params["side"] == "right") else "right" ),
                    "@item-name": xml_encode( item.name ),
                    "@upgrade-name": xml_encode( upgrade.get_name() ),
                    "@upgrade-title": xml_encode( upgrade.get_title() ),
                    "@upgrade-cost": xml_encode( "%d" % upgrade.get_cost() ),
                    "@gold-needed": xml_encode( "%d" % ( upgrade.get_cost() - money ) ), # Only used for too-expensive template
                    "@upgrades-remaining": xml_encode( "%d" % remaining_upgrades ),
                    "@upgrades-remaining-pluralizer": xml_encode( ("s" if (remaining_upgrades > 1) else "") ) # Grammar technicality :)
                })

                # Compile template
                node = template.compile_node_by_id("insert")

                # Add it to the root's upgrades group
                root.find_node_by_id("ext.available-upgrades").add_node(node)

        # If we've upgraded the item all that we can, then we should display a "upgrades done" type of message
        else:

            # Fetch insert template
            template = self.fetch_xml_template( "inventory.item.upgrades.insert", version = "out-of-upgrades" ).add_parameters({
                "@item-name": xml_encode( item.name ) # Don't even need this...
            })

            # Compile template
            node = template.compile_node_by_id("insert")

            # Add it to the root's upgrades group
            root.find_node_by_id("ext.available-upgrades").add_node(node)


        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)


        """ Slide effect """
        # Grab a reference to the inventory directory itself, so that we can slide it out of the way
        directory = self.get_widget_by_id("inventory-home")

        # Show options widget on the left?
        if ( params["side"] == "left" ):

            # slide the directory off to the righit
            directory.slide(DIR_RIGHT, amount = widget.get_width() + 20, delay = 0)


            # Position the options widget just to the left of the directory (mostly off-screen)
            widget.slide(DIR_LEFT, widget.get_width() + 20, animated = False)

            # Now have the options menu slide into view...
            widget.slide(None)

            # Remember which side we're on...
            widget.set_attribute("side", params["side"])


        # Okay, show it on the right, then...
        elif ( params["side"] == "right" ):

            # Slide the directory out of the way
            directory.slide(DIR_LEFT, amount = widget.get_width(), delay = 0)


            # Position the options widget just to the right of the directory
            widget.slide(DIR_RIGHT, amount = widget.get_width() + 20, animated = False)

            # Now, slide the options widget into view...
            widget.slide(None)

            # Remember which side we're on...
            widget.set_attribute("side", params["side"])


        widget.set_id("inventory-allitems-options")

        # Add the overlay!
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the options menu for one of the items in the "all of my items" list
    def handle_hide_inventories_inventory_all_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Get the overlay representing the HPane with the options in it (equip, do nothing, etc.)
        widget = self.get_widget_by_id("inventory-allitems-options")

        # Get the inventory directory itself
        directory = self.get_widget_by_id("inventory-home")


        # Which side were we on?
        side = widget.get_attribute("side")

        if (side == "left"):

            # HIde and slide!
            widget.hide()

            widget.slide(
                DIR_LEFT,
                amount = widget.get_width() + 20,
                on_complete = "previous-page"
            )

        elif (side == "right"):

            # Slide and hide!
            widget.hide()

            # Slide the details off the screen...
            widget.slide(
                DIR_RIGHT,
                amount = directory.get_width() + 20,
                on_complete = "previous-page"#lambda widget, a = self, b = [], n = network_controller, c = universe, d = active_map, e = session, wd = widget_dispatcher, f = text_renderer, g = save_controller, p = {"do": "show-inventory.equipped:hide-options.cleanup"}: a.handle_selection(p, b, n, c, d, e, wd, f, g, widget)
            )

        # Return the directory to default slide (no slide)
        directory.slide(None)

        # Return events
        return results


    # slide in the "confirm upgrade" page for any given item (equipped or all, it's all the same)
    def handle_show_inventories_inventory_item_upgrade_confirm_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get a reference to the upgrade in question (for retrieving title / cost data)
        upgrade = universe.get_acquired_item_by_name( params["item-name"] ).get_available_upgrade_by_name( params["upgrade-name"] )


        # How much gold does the player have?
        money = int( universe.get_session_variable("core.gold.wallet").get_value() )

        # Can we afford this upgrade?
        template_version = ("affordable" if ( money >= upgrade.get_cost() ) else "unaffordable")


        # Fetch template
        template = self.fetch_xml_template( "inventory.item.upgrade.confirm", version = template_version ).add_parameters({
            "@x": xml_encode( "%d" % ( 0 if ( params["side"] == "left" ) else (20 + int(PAUSE_MENU_WIDTH / 2)) ) ), # kinda hacky!
            "@y": xml_encode( "%d" % int(PAUSE_MENU_Y) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ), # hard-coded
            "@item-name": xml_encode( params["item-name"] ),
            "@upgrade-name": xml_encode( upgrade.get_name() ),
            "@upgrade-title": xml_encode( upgrade.get_title() ),
            "@upgrade-cost": xml_encode( "%d" % upgrade.get_cost() )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("item-upgrade-confirm")


        # Fetch the "item options" page, the active page as it were
        page2 = self.get_active_page()

        # Slide it away
        page2.slide(DIR_UP, amount = SCREEN_HEIGHT)

        # Hide
        page2.hide()


        # Position widget to slide in from bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Slide into position, with animation
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Show the "replace item" page for any given item (equipped or all, doesn't matter here)
    def handle_show_inventories_inventory_item_replace_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Grab a reference to the item we'll be equipping (maybe)
        new_item = universe.get_acquired_item_by_name( params["item-name"] )


        # Fetch the template for the popup
        template = self.fetch_xml_template("inventory.menu.replace").add_parameters({
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ), # hard-coded
            "@x": xml_encode( "%d" % 0 ), # hard-coded
            "@y": xml_encode( "%d" % 0 )  # hard-coded
        })

        # Compile the template
        root = template.compile_node_by_id("menu")


        # Now we should loop through all equipped items and inject them as options...
        for old_item in universe.get_equipped_items():

            # Fetch iter template
            template = self.fetch_xml_template("inventory.menu.replace.insert").add_parameters({
                "@item-title": xml_encode( old_item.title ),
                "@old-item-name": xml_encode( old_item.name ),
                "@new-item-name": xml_encode( new_item.name )
            })

            # Compile iter template
            node = template.compile_node_by_id("insert")

            # Add it to the list
            root.find_node_by_id("ext.equipped-items").add_node(node)


        # Create the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("inventory-replace-item-menu")


        # Slide all of the previous pages farther over, except for the root pause menu
        for page in self.get_visible_pages():

            page.slide(DIR_RIGHT, amount = widget.get_width() + 20, incremental = True)


        # Position the new page off to the side at first, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Then, slide it into default position
        widget.slide(None)


        # Add the new page to the menu
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the "replace item" page
    def handle_hide_inventories_inventory_item_replace_options_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Handle to the replace item page
        widget = self.get_widget_by_id("inventory-replace-item-menu")


        # Set all pages to slide one page back
        for page in self.get_visible_pages():

            page.slide(DIR_RIGHT, amount = -( widget.get_width() + 20 ), incremental = True)


        # Also, we should hide and get rid of the page we're leaving
        widget.hide(
            on_complete = "previous-page"
        )

        # Return events
        return results


    # Equip a given item in the game
    def handle_game_equip_item_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # What's the item's name?
        item_name = params["item-name"]

        # Equip the item...
        universe.equip_item_by_name(item_name)

        # Update UI
        self.refresh_pages(control_center, universe)

        # Return events
        return results


    # Unequip a given item in the game
    def handle_game_unequip_item_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Item name!
        item_name = params["item-name"]

        # Take it off!
        universe.unequip_item_by_name(item_name)

        # Update UI
        self.refresh_pages(control_center, universe)

        # Return events
        return results


    # Upgrade a given item in the game
    def handle_game_upgrade_item_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Item name
        item_name = params["item-name"]

        # Upgrade name
        upgrade_name = params["upgrade-name"]


        log2( (item_name, upgrade_name) )


        # Fetch the given item
        item = universe.get_acquired_item_by_name(item_name)

        # Validate
        if (item):

            log2(item)

            # Get a reference to the upgrade itself
            upgrade = item.get_available_upgrade_by_name(upgrade_name)

            # Validate
            if (upgrade):

                # Deduce the cost of the upgrade from theh player's gold count
                universe.increment_session_variable(
                    "core.gold.wallet",
                    -1 * upgrade.get_cost()
                )

                # Add a newsfeeder update to the universe
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_ITEM_UPGRADE,
                    "item-title": item.get_title(),
                    "upgrade-title": upgrade.get_title()
                })


                # Lastly, commit the given upgrade to the item
                item.commit_and_disavow_upgrade_by_name(upgrade_name)


                # Unequip, then re-equip the item so that the upgrade takes effect immediately
                universe.unequip_item_by_name( item.get_name() )
                universe.equip_item_by_name( item.get_name() )


                # Execute the "upgraded-item" achievement hook
                universe.execute_achievement_hook( "upgraded-item", control_center )


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)

        # Return events
        return results


    # Replace one item with another item in the game
    def handle_game_replace_item_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Handle to the replace item page
        widget = self.get_widget_by_id("inventory-replace-item-menu")


        """ Item management """
        # Old / new item names
        (old_item_name, new_item_name) = (
            params["old-item-name"],
            params["new-item-name"]
        )


        # Take off the old item
        universe.unequip_item_by_name(old_item_name)

        # Put on the new item
        universe.equip_item_by_name(new_item_name)


        """ Widget management / animation """
        # Update UI
        self.refresh_pages(control_center, universe, curtailed_count = 2)#user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller)

        # Set all pages (redundantly including the replace item page for now) to slide to "default" position
        for page in self.get_visible_pages():

            page.slide(None)


        # The replace item page should slide off to the left, though...
        widget.slide(DIR_LEFT, percent = 1.0)

        # We want to hide both the "replace item" page and the "item options" page...
        for widget_id in ("inventory-replace-item-menu", "inventory-allitems-options"):

            self.get_widget_by_id(widget_id).hide()

        # Return events
        return results


    # Show all of the player's active quests in a horizontally-sliding thing
    def handle_show_quests_active_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        """ Build base directory """
        # Fetch active quests
        quests = universe.get_active_quests()

        # Fetch directory template
        template = self.fetch_xml_template("quests.directory").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@quest-type": xml_encode( "Active" ),
            "@count": xml_encode( "%d" % len(quests) )
        })

        # Compile root
        root = template.compile_node_by_id("directory")


        """ Insert quests """
        # Potential zebra striping
        zebra = False

        # Loop quests
        for quest in quests:

            # Fetch quest insert
            template = self.fetch_xml_template(
                "quests.insert",
                version = "active" if (zebra) else "active"
            ).add_parameters({
                "@thumbnail": xml_encode( os.path.join( UNIVERSES_PATH, universe.get_name(), "gfx", quest.get_graphic() ) ),
                "@quest-name": xml_encode( quest.get_name() ),
                "@quest-title": xml_encode( localization_controller.translate( quest.get_title() ) ),
                "@quest-description": xml_encode( universe.translate_session_variable_references( localization_controller.translate( quest.get_description() ), control_center ) ),
                #"@quest-description": xml_encode( "%s" % quest.get_description() ),
                "@quest-xp": xml_encode( "%s" % quest.get_xp_label() )
            })

            # Compile template
            node = template.compile_node_by_id("insert")

            # Inject the new node into the appropriate root...
            root.find_node_by_id("ext.quests").add_node(node)


            # Alternate zebra
            zebra = (not zebra)


        # Create the directory widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("quests-home")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show all of the player's finished quests in a horizontally-sliding thing.
    # This shows both "completed" and "failed" quests.
    def handle_show_quests_finished_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        """ Build base directory """
        # Fetch finished quests
        quests = universe.get_finished_quests()

        # Fetch directory template
        template = self.fetch_xml_template("quests.directory").add_parameters({
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@quest-type": xml_encode( "Finished" ),
            "@count": xml_encode( "%d" % len(quests) )
        })

        # Compile root
        root = template.compile_node_by_id("directory")


        """ Insert quests """
        # Potential zebra striping
        zebra = False

        # Loop quests
        for quest in quests:

            # Fetch quest insert
            template = self.fetch_xml_template(
                "quests.insert",
                version = "active" if (zebra) else "active"
            ).add_parameters({
                "@thumbnail": xml_encode( os.path.join( UNIVERSES_PATH, universe.get_name(), "gfx", quest.get_graphic() ) ),
                "@quest-name": xml_encode( quest.get_name() ),
                "@quest-title": xml_encode( localization_controller.translate( quest.get_title() ) ),
                "@quest-description": xml_encode( universe.translate_session_variable_references( localization_controller.translate( quest.get_description() ), control_center ) ),
                #"@quest-description": xml_encode( "%s" % quest.get_description() ),
                "@quest-xp": xml_encode( "%s" % quest.get_xp_label() )
            })

            # Compile template
            node = template.compile_node_by_id("insert")

            # Inject the new node into the appropriate root...
            root.find_node_by_id("ext.quests").add_node(node)


            # Alternate zebra
            zebra = (not zebra)


        # Create the directory widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("quests-home")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show all updates belonging to a given quest, by quest name
    def handle_show_quest_updates_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        """ Controllers """
        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        """ Build updates directory """
        # Scope
        root = None


        # Fetch the given quest (or, try)
        quest = universe.get_quest_by_name( params["quest-name"] )

        # Validate
        if (quest):

            # Get all quest updates
            updates = quest.get_active_updates()


            # Fetch updates directory template
            template = self.fetch_xml_template(
                "quests.insert.details",
                version = "normal" if ( len(updates) > 0 ) else "no-updates"
            ).add_parameters({
                "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
                "@count": xml_encode( "%d" % len(updates) )
            })

            # Compile root
            root = template.compile_node_by_id("directory")


            """ Insert updates, if/a """
            # Loop updates, looping in reverse order
            for i in range( len(updates) - 1, -1, -1 ):

                # Convenience
                update = updates[i]


                # Fetch quest update insert
                template = self.fetch_xml_template("quests.insert.details.insert").add_parameters({
                    "@update-index": xml_encode( "%d" % (1 + i) ),
                    "@update-description": xml_encode( universe.translate_session_variable_references( localization_controller.translate( update.get_description() ), control_center ) )
                })

                # Compile template
                node = template.compile_node_by_id("insert")

                # Inject the new node into the appropriate root...
                root.find_node_by_id("ext.updates").add_node(node)


        # Create the directory widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("quests-home:details")


        # Fetch page 1
        page1 = self.get_widget_by_id("quests-home")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show controls customization menu (in-game pause menu version).
    # This menu checks the most recently used device to determine whether to edit keyboard or gamepad controls.
    def handle_show_options_controls_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()


        # Scope
        root = None


        # Most recently used the keyboard?
        if ( input_controller.get_last_used_device() == "keyboard" ):

            # Fetch keyboard controls template
            template = self.fetch_xml_template("options.controls.keyboard").add_parameters({
                "@x": xml_encode( "%d" % 0 ),
                "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
            })

            # Parameterize with keyboard translations
            template.add_parameters({
                "@keyboard-translations.left": xml_encode( input_controller.fetch_keyboard_translation("left") ),
                "@keyboard-translations.right": xml_encode( input_controller.fetch_keyboard_translation("right") ),
                "@keyboard-translations.up": xml_encode( input_controller.fetch_keyboard_translation("up") ),
                "@keyboard-translations.down": xml_encode( input_controller.fetch_keyboard_translation("down") ),
                "@keyboard-translations.dig-left": xml_encode( input_controller.fetch_keyboard_translation("dig-left") ),
                "@keyboard-translations.dig-right": xml_encode( input_controller.fetch_keyboard_translation("dig-right") ),
                "@keyboard-translations.bomb": xml_encode( input_controller.fetch_keyboard_translation("bomb") ),
                "@keyboard-translations.suicide": xml_encode( input_controller.fetch_keyboard_translation("suicide") ),
                "@keyboard-translations.interact": xml_encode( input_controller.fetch_keyboard_translation("interact") ),
                "@keyboard-translations.minimap": xml_encode( input_controller.fetch_keyboard_translation("minimap") ),
                "@keyboard-translations.net-chat": xml_encode( input_controller.fetch_keyboard_translation("net-chat") ),       # Keyboard only!
                "@keyboard-translations.skill1": xml_encode( input_controller.fetch_keyboard_translation("skill1") ),
                "@keyboard-translations.skill2": xml_encode( input_controller.fetch_keyboard_translation("skill2") )
            })

            # Create root node
            root = template.compile_node_by_id("menu")

        # Most recently used gamepad (assume)
        else:

            # Fetch keyboard controls template
            template = self.fetch_xml_template("options.controls.gamepad").add_parameters({
                "@x": xml_encode( "%d" % 0 ),
                "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
            })

            # Parameterize with gamepad translations
            template.add_parameters({
                "@gamepad-translations.left": xml_encode( input_controller.fetch_gamepad_translation("left") ),
                "@gamepad-translations.right": xml_encode( input_controller.fetch_gamepad_translation("right") ),
                "@gamepad-translations.up": xml_encode( input_controller.fetch_gamepad_translation("up") ),
                "@gamepad-translations.down": xml_encode( input_controller.fetch_gamepad_translation("down") ),
                "@gamepad-translations.dig-left": xml_encode( input_controller.fetch_gamepad_translation("dig-left") ),
                "@gamepad-translations.dig-right": xml_encode( input_controller.fetch_gamepad_translation("dig-right") ),
                "@gamepad-translations.bomb": xml_encode( input_controller.fetch_gamepad_translation("bomb") ),
                "@gamepad-translations.suicide": xml_encode( input_controller.fetch_gamepad_translation("suicide") ),
                "@gamepad-translations.interact": xml_encode( input_controller.fetch_gamepad_translation("interact") ),
                "@gamepad-translations.minimap": xml_encode( input_controller.fetch_gamepad_translation("minimap") ),
                "@gamepad-translations.skill1": xml_encode( input_controller.fetch_gamepad_translation("skill1") ),
                "@gamepad-translations.skill2": xml_encode( input_controller.fetch_gamepad_translation("skill2") ),
                "@gamepad-translations.escape": xml_encode( input_controller.fetch_gamepad_translation("escape") ),
                "@gamepad-translations.enter": xml_encode( input_controller.fetch_gamepad_translation("enter") ),
                "@gamepad-translations.menu-left": xml_encode( input_controller.fetch_gamepad_translation("menu-left") ),
                "@gamepad-translations.menu-right": xml_encode( input_controller.fetch_gamepad_translation("menu-right") ),
                "@gamepad-translations.menu-up": xml_encode( input_controller.fetch_gamepad_translation("menu-up") ),
                "@gamepad-translations.menu-down": xml_encode( input_controller.fetch_gamepad_translation("menu-down") )
            })

            # Create root node
            root = template.compile_node_by_id("menu")


        # Convert node to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        # Set new widget's id
        widget.set_id("options-controls")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Edit a keyboard control.  Show the "press any key" prompt.
    def handle_show_edit_keyboard_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.keyboard.prompt").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@key": xml_encode( "%s" % params["key"] ),
            "@todo": xml_encode( "%s" % params["todo"] )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-keyboard-control")


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update a given keyboard control
    def handle_game_update_keyboard_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # Which input to update?
        key = params["key"]

        # New value
        keycode = int( params["keycode"] )


        # If the player hits ESC, then just do nothing... I don't allow the use of the ESC key.
        if (keycode == K_ESCAPE):

            # Hide keyboard prompt
            self.fire_event("hide")

        # Any other key (I suppose?) is fine!
        else:

            # Here's a terrible hack.  I want to prevent the user
            # from using ENTER to show the net chat typing area.
            if ( (key == "net-chat") and (keycode == K_RETURN) ):

                # Find error label
                label = self.get_widget_by_id("edit-keyboard-control").find_widget_by_id("error")

                # Validate
                if (label):

                    # Show an error message
                    label.set_text("You cannot use the [color=special]ENTER[/color] key for this action.")


                # Disable the "hide" listener (prevent the hide event from firing)
                listener = self.get_widget_by_id("edit-keyboard-control").find_widget_by_id("keypress-listener")

                # Validate
                if (listener):

                    # Reset
                    listener.reset()

            # Otherwise, update normally
            else:

                # Update the given key definition
                input_controller.update_keyboard_setting(
                    key = key,
                    value = keycode
                )


                # Execute the "customized-control" achievement hook
                universe.execute_achievement_hook("customized-controls", control_center)


                # Refresh UI
                self.refresh_pages(control_center, universe, curtailed_count = 1)

                # Hide keyboard prompt
                self.fire_event("hide")

        # Return events
        return results


    # Show the "are you sure?" dialog for resetting keyboard controls
    def handle_show_reset_keyboard_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "are you sure?" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.keyboard.default").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("reset-keyboard-controls")


        # Position the confirmation page to slide in from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Slide to default location
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Reset all keys to default for the keyboard device
    def handle_game_reset_keyboard_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Reset the keyboard controls
        control_center.get_input_controller().reset_keyboard_controls()


        # Add a newsfeeder item
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GAME_KEYBOARD_RESET,
            "title": control_center.get_localization_controller().get_label("keyboard-reset:title"),
            "content": control_center.get_localization_controller().get_label("keyboard-reset:message")
        })


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)


        # Return events
        return results


    # Edit a gamepad control.  Show the "press a button on the gamepad" prompt.
    def handle_show_edit_gamepad_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.gamepad.prompt").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@key": xml_encode( "%s" % params["key"] ),
            "@todo": xml_encode( "%s" % params["todo"] )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-gamepad-control")


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update a given gamepad control.
    def handle_game_update_gamepad_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # Which key (action) are we editing?
        key = params["key"]

        # Fetch the gamepad input event
        event = params["gamepad-event"]


        # Update the given action using that event
        input_controller.update_gamepad_setting(key, event)


        # Execute the "customized-control" achievement hook
        universe.execute_achievement_hook("customized-controls", control_center)


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)

        # Return events
        return results


    # ESC will abort the "edit gamepad control" prompt
    def handle_abort_edit_gamepad_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Which key got pressed?
        keycode = int( params["keycode"] )

        # Is it the ESC key?
        if (keycode == K_ESCAPE):

            # Let's fire a "back" event to page back...
            self.fire_event("hide")

            log2("hide me")

        # Return events
        return results


    # Show the "are you sure?" dialog for resetting gamepad controls
    def handle_show_reset_gamepad_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "are you sure?" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.gamepad.default").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@device-name": xml_encode( "%s" % control_center.get_input_controller().get_active_device_name() )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("reset-gamepad-controls")


        # Position the confirmation page to slide in from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Slide to default location
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Reset all gamepad controls for the current gamepad device
    def handle_game_reset_gamepad_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Reset the active device's controls
        control_center.get_input_controller().reset_active_gamepad_controls()


        # Add a newsfeeder item
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GAME_GAMEPAD_RESET,
            "title": control_center.get_localization_controller().get_label("gamepad-reset:title"),
            "content": control_center.get_input_controller().get_active_device_name()
        })


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)


        # Return events
        return results


    # Save control preferences (this saves both keyboard and gamepad, kind of redundant in that regard)
    def handle_game_save_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Save the controls
        control_center.get_input_controller().save()

        # Post a newsfeeder item confirming the save
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GAME_CONTROLS_SAVED,
            "title": control_center.get_localization_controller().get_label("controls-saved:title"),
            "content": params["message"]
        })


        # Return events
        return results


    # Show the in-game achievements menu
    def handle_show_options_achievements_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Fetch achievement directory template
        template = self.fetch_xml_template("options.achievements").add_parameters({
            "@x": xml_encode( "%d" % 0 ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Create root node
        root = template.compile_node_by_id("menu")


        # Now we want to loop through the current universe's achievements.
        # Start by getting the list...
        achievements = universe.get_achievements()

        # Validate that we have a list for the given universe
        if ( len(achievements) > 0 ):

            # Create a new, temporary event controller
            event_controller = control_center.create_event_controller()


            # Load default markup for each achievement insert
            template = self.fetch_xml_template("options.achievements.insert")

            # Loop through all achievements that correctly implement the get-status hook.
            for achievement in [ o for o in achievements if o.has_hook("get-status") ]:

                # If we have already completed the achievement, we don't need to run the get-status script
                if ( achievement.is_complete() ):

                    # We do, though, need to update the session variable we use for the phrase
                    universe.get_session_variable("tmp.achievement.get-status").set_value("Complete")

                # If we've failed it, we alter that phrase...
                elif ( not achievement.is_active() ):

                    # Update phrase
                    universe.get_session_variable("tmp.achievement.get-status").set_value("Failed")

                # Still active; we need to get the status phrase via script...
                else:

                    # Run the get-status hook for this achievement.
                    # It should (if scripted correctly) dump the status of the achievement into a session variable.
                    event_controller.load(
                        achievement.get_hook("get-status")
                    )

                    # Execute all non-blocking logic
                    event_controller.loop(control_center, universe)


                # Update markup for this particular achievement
                template.add_parameters({
                    "@title": xml_encode( "%s" % localization_controller.translate( achievement.get_title() ) ),
                    "@status": xml_encode( "%s" % universe.get_session_variable("tmp.achievement.get-status").get_value() ),
                    "@description": xml_encode( "%s" % localization_controller.translate( achievement.get_description() ) )
                })


                # Compile the node and add it to the ext.achievements node
                root.find_node_by_id("ext.achievements").add_node(
                    template.compile_node_by_id("insert")
                )

        #print root.compile_xml_string()
        #print 5/0


        # Convert node to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        # Set new widget's id
        widget.set_id("options-achievements")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # show the transaction history screen
    def handle_show_options_transactions_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()


        # Fetch achievement directory template
        template = self.fetch_xml_template("options.transactions").add_parameters({
            "@x": xml_encode( "%d" % 0 ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Create root node
        root = template.compile_node_by_id("menu")


        # Fetch transaction history
        records = universe.get_historical_records_by_type("purchases")

        # If no transaction exists, display an "n/a" message
        if ( len(records) == 0 ):

            # Fetch generic insert
            template = self.fetch_xml_template("options.transactions.insert", version = "n/a").add_parameters({
            })

            # Add generic message
            root.find_node_by_id("ext.purchases").add_node(
                #XMLParser().create_node_from_xml(template).find_node_by_id("insert")
                template.compile_node_by_id("insert")
            )

        # Loop through historical record group "purchases"
        else:

            # Loop in reverse order
            records.reverse()


            # Loop
            for record in records:

                # Fetch template
                template = self.fetch_xml_template("options.transactions.insert", version = "normal").add_parameters({
                    "@purchase-details": xml_encode( "%s" % universe.translate_session_variable_references(record, control_center) )
                })

                # Add transaction record
                root.find_node_by_id("ext.purchases").add_node(
                    template.compile_node_by_id("insert")
                )


        # Convert node to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        # Set new widget's id
        widget.set_id("options-statistics")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show the gameplay statistics screen
    def handle_show_options_statistics_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()


        # Fetch achievement directory template
        template = self.fetch_xml_template("options.statistics").add_parameters({
            "@x": xml_encode( "%d" % 0 ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@time-played": xml_encode( "%s" % format_timedelta( 0, int( universe.get_session_variable("core.time.played").get_value() ) / 60 ) ),
            "@character-level": xml_encode( "%s" % universe.get_session_variable("core.player1.level").get_value() ),
            "@character-name": xml_encode( "%s" % universe.get_session_variable("core.player1.name").get_value() ),
            "@total-digs": xml_encode( "%s" % universe.get_session_variable("stats.digs").get_value() ),
            "@enemies-killed": xml_encode( "%s" % universe.get_session_variable("stats.enemies-killed").get_value() ),
            "@gold-collected": xml_encode( "%s" % universe.count_collected_gold_pieces() ),
            "@items-acquired": xml_encode( "%s" % universe.get_session_variable("stats.items-bought").get_value() ),
            "@gold-spent": xml_encode( "%s" % universe.get_session_variable("stats.gold-spent").get_value() ),
            "@npcs-killed": xml_encode( "%s" % universe.get_session_variable("npc.count.dead").get_value() ),
            "@quests-completed": xml_encode( "%d" % len( universe.get_completed_quests() ) ),
            "@quests-possible": xml_encode( "%d" % len( universe.get_all_quests() ) ),
            "@achievements-completed": xml_encode( "%d" % len( [o for o in universe.get_achievements() if o.is_complete()] ) ),
            "@achievements-possible": xml_encode( "%d" % len( universe.get_achievements() ) ),
        })

        # Create root node
        root = template.compile_node_by_id("menu")


        # Convert node to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        # Set new widget's id
        widget.set_id("options-statistics")


        # Fetch page 1
        page1 = self.get_widget_by_id("root")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)


        # Position new page offscreen, with a little padding
        widget.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Slide in to main position
        widget.slide(None)


        # Add the inventory page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Hide event (no transition except simple fade)
    def handle_hide_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch current page
        page = self.get_active_page()

        # Also mark the current page as "locked" as we begin to transition away from it
        page.set_attribute( "-locked", "yes" )


        # Validate
        if (page):

            # Set hard-coded param
            self.widgets[-1].set_attribute("-pages", "1")

            # Hide
            page.hide(
                on_complete = "transparent:back" # Borrow event, we're just paging back anyway
            )

        # Return events
        return results


    # Begin moving back to the previous page
    def handle_back_event(self, event, control_center, universe):

        # Track local results
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
                    on_complete = "transparent:slide-back"
                )


                # If we have a widget below...
                if ( len(self.widgets) > 1 ):

                    # Start the unslide animation to give it a headstart
                    self.widgets[-2].slide(None)


            # Slide everything back left?
            elif ( params["slide"] == "left" ):

                # Disable exclusive status for top page, assuming it is exclusive in the first place...
                self.widgets[-1].set_attribute("exclusive", "no")


                # Slide and hide the top page
                self.widgets[-1].slide(DIR_LEFT, percent = 1.0)

                # Hide
                self.widgets[-1].hide(
                    on_complete = "transparent:slide-back"
                )


                # If we have a widget below...
                if ( len(self.widgets) > 1 ):

                    # Start the unslide animation to give it a headstart
                    self.widgets[-2].slide(None)


            # Slide everything back down?
            elif ( params["slide"] == "down" ):

                # Disable exclusive status for top page, assuming it is exclusive in the first place...
                self.widgets[-1].set_attribute("exclusive", "no")


                # Slide and hide the top page
                self.widgets[-1].slide(DIR_DOWN, amount = SCREEN_HEIGHT)

                # Hide
                self.widgets[-1].hide(
                    on_complete = "transparent:slide-back"
                )


                # If we have a widget below...
                if ( len(self.widgets) > 1 ):

                    # Start the unslide animation to give it a headstart
                    self.widgets[-2].slide(None)


        else:

            self.widgets[-1].hide(
                on_complete = "transparent:back"
            )

        # Return events
        return results


    # Finish up a "back" call, moving to the previous page, transparently...
    def handle_transparent_back_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # The page that fired this event tracked the "page count"
        # via an attribute.
        pages = int( self.widgets[-1].get_attribute("-pages") )

        # Page back as specified
        self.page_back(pages)

        # Return events
        return results


    # Finish up a "back" call, moving to the previous page, transparently.
    # With this event, we also undo any slide settings on the previous page...
    def handle_transparent_slide_back_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Page back by however many pages
        self.page_back(
            int( self.widgets[-1].get_attribute("-pages") )
        )

        # Show and "unslide" the top page, if/a
        if ( len(self.widgets) > 0 ):

            # Restore to default position
            self.widgets[-1].slide(None)

            # Show
            self.widgets[-1].show()

        # Return events
        return results


    # Resume the game, finally!
    def handle_resume_game_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Dismiss lightbox effect
        self.lightbox_controller.set_target(0)


        # Fetch splash controller
        splash_controller = control_center.get_splash_controller()


        # Hook into the splash controller
        #splash_controller.hook(self)

        # Dismiss the splash controller, calling to resume game action once done...
        splash_controller.dismiss(
            on_complete = "game:unpause"
        )


        # Let's tell the MenuStack that the HMenu can have focus, in preparation for the next pause menu use...
        self.get_widget_by_id("root").set_active_widget_by_id("navbar")


        (hmenu, row_menu) = (
            self.get_widget_by_id("root").get_widget_by_id("navbar"),
            self.get_widget_by_id("root").get_widget_by_id("content")
        )


        # Make sure we remove focus from the active grid menu...
        hmenu.blur()

        # Also, for now let's take focus away from the HMenu as well.  We'll give it back (for next time) when the pause menu disappears.
        row_menu.blur()


        hmenu.slide(DIR_LEFT, percent = 1.0)
        row_menu.slide(DIR_RIGHT, percent = 1.0)


        # Dismiss the PauseMenu, but preserve the "root" overlay (with the nav bar) for now.
        self.get_widget_by_id("root").hide(
            on_complete = "kill"
        )

        # Return events
        return results


    # Return to the main menu
    def handle_leave_game_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the window controller
        window_controller = control_center.get_window_controller()

        # Hook into window controller
        window_controller.hook(self)


        # Fade window, raising event when done
        window_controller.fade_out(
            on_complete = "fwd.finish:leave-game"
        )


        # Return events
        return results


    # Receive forwarded event from the window controller, indicating that the app-level fade has completed
    # and we should commit the "leave game" event now.
    def handle_fwd_finish_leave_game_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the window controller
        window_controller.unhook(self)


        # Queue an app-level event
        results.add(
            action = "app:leave-game"
        )

        # Restore background music to 100%
        control_center.get_sound_controller().set_background_ratio(1.0)


        # Get current language preference
        language = control_center.get_localization_controller().get_language()

        # Calculate path to this universe's localization data
        path = os.path.join( UNIVERSES_PATH, universe.get_name(), "localization", "%s.xml" % language )

        # Validate path
        if ( os.path.exists(path) ):

            # Unload universe's relative localization data
            control_center.get_localization_controller().unload(path)


        # App-level fade back in to show the game again
        window_controller.fade_in()


        # Return events
        return results



    # Handle a kill event; trash this menu.
    def handle_kill_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Disable pause lock on the menu controller as we prepare to resume gameplay.
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })


        # Done with the pause menu widget
        self.set_status(STATUS_INACTIVE)


        # Return events
        return results
