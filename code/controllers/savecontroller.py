import os, sys
import shutil

import time

from datetime import datetime

from stat import ST_MTIME

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import ensure_path_exists, remove_folder, xml_encode, xml_decode, safe_round, logn

from code.constants.common import LAYER_BACKGROUND, LAYER_FOREGROUND, MODE_GAME

from code.constants.paths import CONFIG_PATH

MAX_SAVE_TITLE_LENGTH = 50

class SaveController:

    def __init__(self):
        return


    # Check to see if a save path exists
    def does_save_exist(self, path):

        # Simple check
        return os.path.exists(path)


    def load_from_folder(self, path, control_center, universe, data_only = False):

        # End current session
        universe.end_session(control_center, universe)


        # Validate path
        if ( os.path.exists(path) ):

            # First, clear the active folder
            active_path = os.path.join( universe.get_working_save_data_path(), "active" )

            if ( os.path.exists(active_path) ):

                remove_folder(active_path)


            # Now copy the saved data into the active slot...
            shutil.copytree(path, active_path)

            # Just for fun, let's "touch" the new folder to update its "last modified" time
            os.utime(active_path, None)


            # Lastly, load in the previous game state
            session_file_path = os.path.join( universe.get_working_save_data_path(), "active", "gamestate.xml" )

            # Validate
            if ( os.path.exists(session_file_path) ):

                f = open(session_file_path, "r")
                xml = f.read()
                f.close()

                # Set up a root node
                node = XMLParser().create_node_from_xml(xml)


                # Before we get busy, let's reboot the universe for a fresh start on this save file
                universe.reboot()


                # Load in session variables
                ref_session = node.find_node_by_tag("session")

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

                    # Ask the universe to import the given session
                    universe.import_session(session)


                # Load in historical record data
                ref_historical_records = node.find_node_by_tag("historical-records")

                # Validate
                if (ref_historical_records):

                    # Find each record type
                    for ref_record_type in ref_historical_records.get_nodes_by_tag("historical-record"):

                        # Get the record type key
                        key = ref_record_type.get_attribute("type")

                        # Import recorded events
                        for ref_record in ref_record_type.get_nodes_by_tag("record"):

                            # Raw string
                            universe.add_historical_record(
                                key,
                                ref_record.innerText
                            )


                # Load in worldmap data
                ref_worldmap = node.find_node_by_tag("worldmap")

                # Validate
                if (ref_worldmap):

                    map_data_collection = ref_worldmap.get_nodes_by_tag("map")

                    for ref_map_data in map_data_collection:

                        (name, visible, visited, gold_remaining, completed, completion_time) = (
                            ref_map_data.get_attribute("name"),
                            int( ref_map_data.get_attribute("visible") ) == 1,
                            int( ref_map_data.get_attribute("visited") ) == 1,
                            int( ref_map_data.get_attribute("gold-remaining") ),
                            int( ref_map_data.get_attribute("completed") ) == 1,
                            int( ref_map_data.get_attribute("completion-time") )
                        )

                        if (visible):
                            universe.set_map_as_visible(name)

                        if (visited):
                            universe.set_map_as_visited(name)

                        if (completed):
                            universe.mark_map_as_completed(name)


                        # Update completion time for the relevant map data object.  What a hack!
                        universe.get_map_data(name).completion_time = completion_time


                        universe.set_map_gold_remaining(name, gold_remaining)


                # Load quest status data
                ref_questdata = node.find_node_by_tag("questdata")

                # Validate
                if (ref_questdata):

                    # Check for active quest order of acquisition data
                    ref_active_quests = ref_questdata.find_node_by_tag("active-quests")

                    # Validate
                    if (ref_active_quests):

                        # Loop sequence
                        for ref_active_quest in ref_active_quests.get_nodes_by_tag("active-quest"):

                            # Add to ordered list
                            universe.track_quest_by_name(
                                ref_active_quest.innerText
                            )


                    # Find all quest state data
                    quest_collection = ref_questdata.get_nodes_by_tag("quest")

                    for ref_quest in quest_collection:

                        # Get the name attribute
                        name = ref_quest.get_attribute("name")

                        # Fetch the quest itself...
                        quest = universe.get_quest_by_name(name)

                        # Validate...
                        if (quest):

                            quest.load_memory(ref_quest)


                # Load inventory data
                ref_inventory = node.find_node_by_tag("inventory")

                if (ref_inventory):

                    # Get acquired items
                    ref_acquired_inventory = ref_inventory.find_node_by_tag("acquired")

                    if (ref_acquired_inventory):

                        item_collection = ref_acquired_inventory.get_nodes_by_tag("item")

                        for ref_item in item_collection:

                            # Create a new item
                            item = universe.create_item()

                            # Load item state
                            item.load_state(ref_item)

                            # Add the new item to the player's acquired inventory
                            universe.add_item_to_acquired_inventory(item)


                    # Get equipped inventory
                    ref_equipped_inventory = ref_inventory.find_node_by_tag("equipped")

                    if (ref_equipped_inventory):

                        item_collection = ref_equipped_inventory.get_nodes_by_tag("item")

                        for ref_item in item_collection:

                            # The name of the item
                            name = ref_item.find_node_by_tag("name").innerText

                            # Add the item to the universal inventory record
                            universe.equip_item_by_name(name)


            # Sometimes we only want to load data for the universe, skipping the map activation...
            if (not data_only):

                # Activate the map the player was playing when they created this save
                m = universe.activate_map_on_layer_by_name(
                    universe.get_session_variable("app.active-map-name").get_value(),
                    layer = LAYER_FOREGROUND,
                    game_mode = MODE_GAME,
                    control_center = control_center
                )


                # Validate that we activated a map
                if (m):

                    # Position the player on the new map according to their position at time of save,
                    # unless the map is a linear map!
                    if ( m.get_param("type") != "linear" ):

                        universe.spawn_player_with_name_at_location(
                            name = "player1",
                            x = int( universe.get_session_variable("core.player1.x").get_value() ),
                            y = int( universe.get_session_variable("core.player1.y").get_value() )
                        )


                    # Center the camera on the map the player saved from
                    m.center_camera_on_entity_by_name( universe.get_camera(), "player1", zap = True )


                    # Get player object
                    player = m.get_entity_by_name("player1")

                    # Validate
                    if (player):

                        # Colorify the player by their saved color
                        player.colorify(
                            universe.get_session_variable("core.player1.colors").get_value()
                        )


                # Read in previously completed achievements (these apply to all game saves, unlock once to unlock forever)
                control_center.load_unlocked_achievements(universe)


            """ Begin Debug - I need to force update for old save game files. """
            #universe.update_common_input_translations(control_center)
            """ End Debug """

            return True

        else:
            return False


    # Validate save game titles (e.g. I could add a profanity check if I wanted to, check for empty string, etc.)
    def validate_save_title(self, title):

        # For now, make sure it's a reasonable length
        if ( len(title) == 0 ):

            return False

        elif ( len(title) > MAX_SAVE_TITLE_LENGTH ):

            return False

        else:

            return True


    # Query the reason for not validating
    def get_reason_for_save_title_invalidation(self, title):

        # For now, make sure it's a reasonable length
        if ( len(title) == 0 ):

            return "You must enter a title of at least one letter or number."

        elif ( len(title) > MAX_SAVE_TITLE_LENGTH ):

            return "The length of your title must not exceed %d characters." % MAX_SAVE_TITLE_LENGTH

        else:

            return "Unknown error."


    def save_to_slot(self, slot, universe, quicksave = False, autosave = False, metadata = None):
        logn( "save", "Saving to autosave1...\n")

        # Let's determine the appropriate write path
        path = ""


        if (autosave):

            path = os.path.join( universe.get_working_save_data_path(), "autosave%d" % slot )

        elif (quicksave):

            path = os.path.join( universe.get_working_save_data_path(), "quicksave%d" % slot )

        else:

            path = os.path.join( universe.get_working_save_data_path(), "manualsave%d" % slot )


        # First clear the folder if it already exists...
        if ( os.path.exists(path) ):

            # Remove any data within that folder
            remove_folder(path)


        # I want to ensure that a path to "active" game data always exists, even if we don't have
        # anything on record to copy early in the game.
        ensure_path_exists(
            os.path.join( universe.get_working_save_data_path(), "active" )
        )


        # Now copy the active session data over to that folder...
        shutil.copytree( os.path.join( universe.get_working_save_data_path(), "active" ), path )

        # Also save the thumbnail (well, copy it over...)
        shutil.copyfile( os.path.join("tmp", "temp_surface.resized.png"), os.path.join(path, "thumb.png") )


        # Add any pertinent metadata
        if (metadata):

            f = open( os.path.join(path, "meta.xml"), "w" )
            f.write(metadata)
            f.close()


        # Create a node for game state data
        node = XMLNode("game-state")


        # Create a node for session variables
        ref_session = node.add_node(
            XMLNode("session")
        )

        # Get session variable keys
        keys = universe.session.keys()

        # Sort alphabetically
        keys.sort()

        # Loop session variables
        for key in keys:

            ref_session.add_node(
                XMLNode("variable").set_attributes({
                    "name": xml_encode( "%s" % key ),
                    "value": xml_encode( "%s" % universe.get_session_variable(key).get_value() )
                })
            )


        # Create a node for historical records
        ref_historical_records = node.add_node(
            XMLNode("historical-records")
        )

        # Get known types of historical records
        keys = universe.historical_records.keys()

        # Loop types
        for key in keys:

            # Create a container for this type
            ref_record_type = ref_historical_records.add_node(
                XMLNode("historical-record").set_attributes({
                    "type": xml_encode(key)
                })
            )

            # Now add all records of the current type
            for record in universe.historical_records[key]:

                # Add to record type group
                ref_record_type.add_node(
                    XMLNode("record").set_inner_text(record)
                )


        # Create a node for worldmap data (which maps we've visited, seen, etc.)
        ref_worldmap = node.add_node(
            XMLNode("worldmap")
        )

        # Loop foreground maps (the only maps we can visit / see on the worldmap)
        for key in universe.map_data[LAYER_FOREGROUND]:

            # Convenience
            map_data = universe.map_data[LAYER_FOREGROUND][key]

            ref_worldmap.add_node(
                XMLNode("map").set_attributes({
                    "name": xml_encode( key ),
                    "visible": xml_encode( "1" if (map_data.visible) else "0" ),
                    "visited": xml_encode( "1" if (map_data.visited) else "0" ),
                    "gold-remaining": xml_encode( "%d" % map_data.gold_remaining ),
                    "completed": xml_encode( "1" if (map_data.completed) else "0" ),
                    "completion-time": xml_encode( "%d" % map_data.completion_time )
                })
            )


        # Create a node for quest states
        ref_quests = node.add_node(
            XMLNode("questdata")
        )


        # First, let's save the known quest order in its own node
        ref_active_quests = ref_quests.add_node(
            XMLNode("active-quests")
        )

        # Loop our ordered list
        for name in universe.active_quests_by_name:

            # Track
            ref_active_quests.add_node(
                XMLNode("active-quest").set_inner_text(name)
            )


        # Now loop quests, saving the state for each
        for quest in universe.get_quests():

            # Save quest memory
            ref_quests.add_node(
                quest.save_memory()
            )
            """
            ref_quest = ref_quests.add_node(
                XMLNode("quest").set_attributes({
                    "name": xml_encode( quest.get_name() ),
                    "status": xml_encode( "%s" % quest.get_status() )
                })
            )

            # Loop the updates for this quest; track which ones the player has "unlocked."
            for update in quest.get_updates():

                ref_quest.add_node(
                    XMLNode("update").set_attributes({
                        "name": xml_encode( update.get_name() ),
                        "active": xml_encode( "1" if ( update.is_active() ) else "0" )
                    })
                )
            """


        # Create a node for the player's current inventory
        ref_inventory = node.add_node(
            XMLNode("inventory")
        )


        # Add a node for acquired items
        ref_acquired = ref_inventory.add_node(
            XMLNode("acquired")
        )

        # Loop acquired inventory items
        for item in universe.acquired_inventory:

            ref_acquired.add_node(
                item.save_state()
            )


        # Add a second node for equipped inventory items
        ref_equipped = ref_inventory.add_node(
            XMLNode("equipped")
        )

        # Loop currently equipped inventory
        for item in universe.equipped_inventory:

            ref_equipped.add_node(
                item.save_state()
            )


        # Build path
        session_file_path = os.path.join(path, "gamestate.xml")

        # Save game state to disk
        f = open(session_file_path, "w")
        f.write( node.compile_xml_string() )
        f.close()


        # Update the modification time on the new folder
        os.utime(path, None)


        # If the universe is a story universe (e.g. main story mode), then let's create/update the
        # "last played" file to support the main menu's "continue game" option.
        if ( universe.get_type() == "story" ):

            # Make sure config path exists
            ensure_path_exists(CONFIG_PATH)


            # Create root data node
            root = XMLNode("last-played")


            # Add universe name
            root.add_node(
                XMLNode("universe").set_inner_text(
                    universe.get_name()
                )
            )

            # Add save path
            root.add_node(
                XMLNode("save").set_inner_text(
                    path
                )
            )


            # Open record file
            f = open( os.path.join(CONFIG_PATH, "lastplayed.xml"), "w" )

            # Serialize xml
            f.write(
                root.compile_xml_string()
            )

            # Close file
            f.close()


    def get_path_to_slot(self, universe, slot, quicksave = False, autosave = False):

        # Let's determine the appropriate disk path
        path = ""


        if (autosave):

            path = os.path.join( universe.get_working_save_data_path(), "autosave%d" % slot )

        elif (quicksave):

            path = os.path.join( universe.get_working_save_data_path(), "quicksave%d" % slot )

        else:

            path = os.path.join( universe.get_working_save_data_path(), "manualsave%d" % slot )


        return path


    def construct_metadata_with_title(self, title, universe):

        # Construct the metadata for this save (title, character level, etc.)
        xml = """
            <metadata>
                <timestamp>#TIMESTAMP</timestamp>
                <title>#TITLE</title>
                <character-level>#CHARACTER-LEVEL</character-level>
                <gold-recovered>#GOLD-RECOVERED</gold-recovered>
                <location>#LOCATION</location>
            </metadata>
        """

        logn( "save", "%s, %s, %s\n" % ( universe.get_name(), universe.count_collected_gold_pieces(), universe.count_gold_pieces() ))

        # Calculate overall gold collection percentage (if/a in overworldD)
        gold_recovered_percentage = 0.0

        # Avoid divide-by-zero error
        if ( universe.count_gold_pieces("overworld") > 0 ):

            # Calculate raw percentage
            gold_recovered_percentage = int(
                ( universe.count_collected_gold_pieces("overworld") / float( universe.count_gold_pieces("overworld") ) * 10000.0 )
            ) / 100.0


        # Translate
        translations = {
            "#TIMESTAMP": "%d" % int(time.time()),
            "#TITLE": title,
            "#CHARACTER-LEVEL": "Level %s" % universe.get_session_variable("core.player1.level").get_value(),
            "#GOLD-RECOVERED": "%s%%" % safe_round(gold_recovered_percentage, 1),
            "#LOCATION": "Amandria"
        }

        for key in translations:
            xml = xml.replace(key, translations[key])


        return xml

    def fetch_metadata_from_folder(self, path, universe, quicksave = False, autosave = False):

        # Defaults
        metadata = {
            "timestamp": None,
            "title": "UNTITLED",
            "character-level": "1",
            "gold-recovered": "0%?",
            "location": "",
            "last-modified-date": "Never"
        }

        metadata_path = os.path.join(path, "meta.xml")

        if (os.path.exists(metadata_path)):

            f = open(metadata_path, "r")
            metadata_xml = f.read()
            f.close()

            # Parse metadata XML
            node = XMLParser().create_node_from_xml(metadata_xml)

            # Check each metadata unit...
            for key in metadata:

                ref_elem = node.get_first_node_by_tag("metadata").get_first_node_by_tag(key)

                if (ref_elem):

                    metadata[key] = ref_elem.innerText


        # We'll create a datetime.date object from a timestamp.
        dt = None

        # First check to see if we have a valid timestamp from the savegame's metadata...
        if (metadata["timestamp"] != None):

            dt = datetime.fromtimestamp( int(metadata["timestamp"]) )

        # If we don't, we'll use the folder's last modified date as a fallback... assuming the path exists...
        elif (os.path.exists(path)):

            # Get date data for this path
            stat = os.stat(path)

            mod_time = stat[ST_MTIME]
            dt = datetime.fromtimestamp(mod_time)


        # If we had a chance to create a datetime object, let's use it to populate
        # the metadata hash's "last modified date" value...
        if (dt != None):

            # Simple month conversion hash...
            months = {
                1: "Jan",
                2: "Feb",
                3: "Mar",
                4: "Apr",
                5: "May",
                6: "June",
                7: "July",
                8: "Aug",
                9: "Sept",
                10: "Oct",
                11: "Nov",
                12: "Dec"
            }


            hour = dt.hour
            minute = dt.minute

            formatted_hour = "%d" % (hour % 12)

            if (formatted_hour == "0"):
                formatted_hour = "12"

            formatted_minute = "%d" % minute

            if (minute < 10):
                formatted_minute = "0%d" % minute

            formatted_ampm = "AM"

            if (hour >= 12):
                formatted_ampm = "PM"

            metadata["last-modified-date"] = "%s %d, %d / %s:%s %s" % (months[dt.month], dt.day, dt.year, formatted_hour, formatted_minute, formatted_ampm)


        return metadata
