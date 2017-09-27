import os
import time

import sys

import random

from entities.entities import *
#import from entities.entities 

from particle import Particle, Colorcle, Numbercle
from goldspinner import GoldSpinner

from magicwall import MagicWall

from trigger import Trigger
from wavetracker import WaveTracker

from code.controllers.intervalcontroller import IntervalController
from code.controllers.eventcontroller import EventController

from code.tools.datagrid import DataGrid
from code.tools.xml import XMLParser, XMLNode

from code.game.trap import Trap
from code.game.entities.structures.intersectionqueryresults import IntersectionQueryResults

from code.game.scripting.script import Script

from code.utils.common import log, log2, logn, intersect, offset_rect, wrap_degrees, wrap_index_at_position, ensure_path_exists, f2i, cf, set_alpha_for_glcolor, coalesce, is_numeric

from code.constants.common import *

from code.constants.states import *
from code.constants.death import *


#from gui import Dialog

from code.ui.hackpanel import HackPanel
from code.tools.dialoguepanel import DialoguePanel, DialoguePanelShop, DialoguePanelComputer, DialoguePanelComputerSimple



class Map:

    def __init__(self, name = "Untitled", x = 0, y = 0, options = {}, control_center = None, universe = None, parent = None):

        self.mode = MODE_GAME

        # Track parent universe
        self.parent = parent


        # Map name and title, e.g. ("map1", "Forest Level 1")
        self.name = name
        self.title = "Untitled Area"

        self.saved = False
        self.modified = False

        self.error = None


        # Universal coordinates
        self.x = x
        self.y = y

        self.width = 0
        self.height = 0


        # This map might have one or more sections where the player can
        # fall off the level into an infinite abyss.
        self.fall_regions = []

        # Simple timer to control the fall region effect
        self.fall_region_timer = 0


        # Foreground maps are playable maps, standard maps.
        # Background maps are non-playable, background maps rendered in parallax at 50% size.
        self.layer = LAYER_FOREGROUND


        # A map can use a number of parameters to describe itself.
        # This includes things like "redline," challenge/puzzle room status,
        # overview (for puzzle intros), congratulatory messages, anything!
        # Any given map will have a number of default parameters.
        self.params = {
            "type": "overworld",        # overworld, puzzle, challenge, etc.?
            "redline": "0",             # Does the player die when falling "off" the map?  (In puzzle rooms, challenge rooms, yes!  in overworld maps... MAYBE.)
            "wave": "0",                # Used only by challenge maps to track the enemy wave
            "total-waves": "5",         # Also only used by challenge maps.
            "gold-rotation-size": "-1", # An integer cast into a string.  When > 0, this param determines how many pieces of gold will appear at any given time,
                                        #  and it automatically activates "gold cycling," such that collecting any one piece of gold randomly activates any other piece of gold.

            "stats.bombs-used": 0,      # How many bombs has the player used on this level?
            "stats.enemies-killed": 0,  # How many bad guys has the enemy killed on this level?
            "stats.skills-used": 0      # How many times has the player used a skill on this level?
        }


        # When you enter a map, it will reset a handful of metric-tracking parameters.  These are chiefly used by
        # challenge rooms to determine when the player has completed a given wave, but they can have other uses
        # as well.  For the sake of argument, you begin a new "wave" anytime you enter / re-enter a map (of any
        # map type).  We track these metrics with a special "wave tracker" object.
        self.wave_tracker = WaveTracker()


        # Keep a running tally of however much gold we collect after entering this map.
        # For overworld maps this is useless (map state persists between screens),
        # but we'll use this in puzzle / challenge rooms, and possibly in coop.
        self.local_gold_collected = 0

        # Each map has a "completion time" that tracks how many frames the player
        # has needed in their current attempt to complete this map.  It resets on map visit,
        # so it's really only useful for linear levels.
        self.completion_time = 0


        # For the level editor to know which plane to edit / highlight...
        self.active_plane_z_index = 0


        # Track map status
        self.status = STATUS_ACTIVE

        # Sometimes we'll enter cutscene mode via a script.
        # To enable stacked on/off calls (2 scripts call for a cutscene, we want to wait for both to finish), we'll use a counter.
        self.cutscene_counter = 0


        # An event controller for handling scripted events....
        self.event_controller = EventController()

        # Store any scripts for the map.  Key these by script name...
        self.scripts = {}

        # We don't compile a script until we actually need to run it, just for whatever time it saves us when loading a map...
        self.compiled_scripts = {}

        # For loading/saving purposes (I want to save scripts in the same order as I load them)
        self.preferred_script_order = []


        # The master plane will hold a compilation of all of the planes within the level
        self.master_plane = self.create_plane()

        # At load time, we will load in each plane.  We will revisit this data during planar shifts...
        self.planes = []

        # Sometimes we'll render floating planes (during planar shifts)
        self.floating_planes = []


        # Trigger can activate scripts
        self.triggers = []


        # Simple particle system
        self.particles = []
        self.colorcles = []
        self.numbercles = []

        # Gold spins to the top of the somewhere when collected
        self.gold_spinners = []


        # A map can potentially house one MagicWall object
        self.magic_wall = None


        # A script can flag a reload request
        self.requires_reload = False

        # Sometimes we wait a minute first...
        self.reload_delay = 0


        # A script can tell the map to ask the main app to center the camera immediately
        self.center_camera_immediately = False


        # A script can ask the map to ask the app to ask the screen to ask to shake...
        self.requested_shake_tuple = None


        # Some abilities, such as shield and invisibility, will hook into the app's letterbox to display time/amount remaining...
        self.requested_header_hook = None
        self.requested_footer_hook = None

        # Sometimes the map wants to communicate data via the main app's letterbox
        self.letterbox_queue = []


        # A map may render a message on the screen (e.g. "Collected #x / #y Gold")
        self.status_message = ""


        # A map may need to show a hack panel
        self.hack_panel = None


        # A map may also need to show a dialogue panel
        self.dialogue_panel = None

        # Dialogue panels may lead to branched dialogues...
        self.queued_branch = None


        # A map sometimes will display a map-specific menu (puzzle instructions, victory, failure, etc.)
        self.level_menu = None


        # We can preload a set of user input instructions into
        # a GIF, allowing the player to "move around" according to previously-recording instructions.
        self.replay_data = []

        # Replay cursor
        self.replay_cursor = 0


    # Configure map
    def configure(self, options):

        if ( "x" in options ):
            self.x = int( options["x"] )

        if ( "y" in options ):
            self.y = int( options["y"] )

        if ( "layer" in options ):
            self.layer = int( options["layer"] )

        # Replay data file?
        if ( "replay-file" in options ):

            # Ignore this command if we already loaded replay data (?)
            if ( len(self.replay_data) == 0 ):

                # Validate path
                if ( os.path.exists( options["replay-file"] ) ):

                    # Clear replay data
                    self.replay_data = []

                    # Open file, read data
                    f = open( options["replay-file"], "r" )
                    lines = f.readlines()
                    f.close()

                    # Absorb (extend) given replay data
                    self.replay_data.extend(
                        lines
                    )

                    # Always reset replay cursor
                    self.replay_cursor = 0

                else:
                    log2( "Warning:  Replay file '%s' does not exist!" % options["replay-file"] )

            else:
                log( "Warning:  Replay data already exists for map '%s'" % self.get_name() )


    # Check to see if this map is valid
    def is_valid(self):

        # Just make sure we didn't flag an error (e.g. map already exists on disk) when instantiating this map object
        return (self.error == None)


    def reset(self):

        self.master_plane = self.create_plane()
        self.planes = []


    # Load map data
    def load(self, filepaths, options, control_center):

        """
        # Populate any missing option value using its corresponding default value
        for key in defaults:

            # Not provided?
            if ( not (key in options) ):

                # Default
                options[key] = defaults[key]
        """


        map_data = ""

        if ( "map" in filepaths ):

            if ( os.path.exists( filepaths["map"] ) ):

                f = open( filepaths["map"], "r" )
                map_data = f.read()
                f.close()


        # Does this map have dialogue data?
        dialogue_data = ""

        if ( "dialogue" in filepaths ):

            if ( os.path.exists( filepaths["dialogue"] ) ):

                f = open( filepaths["dialogue"], "r" )
                dialogue_data = f.read()
                f.close()


        self.load_from_string(
            data = {
                "map": map_data,
                "dialogue": dialogue_data
            },
            options = options,
            control_center = control_center
        )

        # Since we loaded this from a file, we have previously saved it...
        self.saved = True

        #self.prepare_weather(WEATHER_STARS)

    def load_from_string(self, data, options = {}, control_center = None):

        # Default options
        flags = {
            "is-editor": False,
            "data-only": False,
        }

        # Update defaults with given data
        flags.update(options)


        # Log map name
        logn( 1, "Loading map '%s'...\n" % self.name)


        # Set up a generic parser
        parser = XMLParser()


        # Scope
        map_node = None

        # Validate key
        if ( "map" in data ):

            # Parse raw map data
            map_node = parser.create_node_from_xml( data["map"] )


        # Scope
        dialogue_node = None

        # Validate key
        if ( "dialogue" in data ):

            # Parse dialogue data
            dialogue_node = parser.create_node_from_xml( data["dialogue"] )

            # Check for invalid dialogue node
            if ( not dialogue_node ):

                # Log error
                logn( 1, "Invalid dialogue data for map '%s'" % self.get_name() )


        #log( "Parsed level data in %s seconds" % (time.time() - a) )
        #a = time.time()


        # Does the map have a title?
        ref_title = map_node.find_node_by_tag("title")

        if (ref_title):

            self.title = ref_title.innerText


        # Check for basic map params
        ref_params = map_node.find_node_by_tag("params")

        # Validate
        if (ref_params):

            # Prepare to load params
            options = {}


            # Find all params
            param_collection = ref_params.get_nodes_by_tag("param")

            # Loop
            for ref_param in param_collection:

                # Save key, value to config hash
                (key, value) = (
                    xml_decode( ref_param.get_attribute("key") ),
                    xml_decode( ref_param.get_attribute("value") )
                )

                # Track
                options[key] = value
                self.set_param(key, value)


            # Configure
            self.configure(options)


        # Begin by loading in planar structures...
        ref_planes = map_node.find_node_by_tag("planes")

        # Validate
        if (ref_planes):

            # Loop defined planes
            for ref_plane in ref_planes.get_nodes_by_tag("plane"):

                # Take next available z index value
                z_index = len(self.planes)

                # Pass the XML to the Planet object so it can load the rings...
                self.add_plane(
                    Plane(ref_plane, z_index)
                )


        # Now that we have all of the planes, we can build the master plane...
        self.master_plane = self.build_master_plane(self.planes)

        #log( "Built planar data in %s seconds" % (time.time() - a) )
        #a = time.time()

        # Find entities node
        ref = map_node.find_node_by_tag("entities")

        # Validate
        if (ref):

            # Loop entities
            for ref_entity in ref.get_nodes_by_tag("entity"):

                # Read in genus
                genus = int( ref_entity.get_attribute("genus") )


                if (genus == GENUS_PLAYER):

                    # Use the XML to create a new Player entity
                    self.master_plane.entities[genus].append(
                        Player().describe(
                            ref_entity.get_attributes()
                        ).customize(
                            ref_entity.get_attributes()
                        )
                    )

                elif (genus == GENUS_RESPAWN_PLAYER):

                    self.master_plane.entities[genus].append(
                        PlayerRespawn().describe(
                            ref_entity.get_attributes()
                        ).customize(
                            ref_entity.get_attributes()
                        )
                    )

                elif (genus == GENUS_ENEMY):

                    # Use the XML...
                    self.master_plane.entities[genus].append( Enemy().describe(
                            ref_entity.get_attributes()
                        ).customize(
                            ref_entity.get_attributes()
                        )
                    )

                elif (genus == GENUS_RESPAWN_ENEMY):

                    self.master_plane.entities[genus].append(
                        EnemyRespawn().describe(
                            ref_entity.get_attributes()
                        ).customize(
                            ref_entity.get_attributes()
                        )
                    )

                elif (genus == GENUS_NPC):

                    species = "generic"

                    if ( ref_entity.has_attribute("species") ):

                        species = ref_entity.get_attribute("species")


                    if ( species == "generic" ):

                        self.master_plane.entities[genus].append(
                            NPC().describe(
                                ref_entity.get_attributes()
                            ).customize(
                                ref_entity.get_attributes()
                            )
                        )

                        # Validate
                        if (dialogue_node):

                            # Load in any dialogue data for the NPC we just created...
                            self.master_plane.entities[genus][-1].load_conversation_data_from_node(dialogue_node)#session)

                    elif ( species == "terminal" ):

                        self.master_plane.entities[genus].append(
                            Terminal().describe(
                                ref_entity.get_attributes()
                            ).customize(
                                ref_entity.get_attributes()
                            )
                        )

                        # Validate
                        if (dialogue_node):

                            # Load in any dialogue data for the NPC we just created...
                            self.master_plane.entities[genus][-1].load_conversation_data_from_node(dialogue_node)#session)

                    elif ( species == "indicator-arrow" ):

                        self.master_plane.entities[genus].append(
                            IndicatorArrow().describe(
                                ref_entity.get_attributes()
                            ).customize(
                                ref_entity.get_attributes()
                            )
                        )

                        # Validate
                        if (dialogue_node):

                            # Load in any dialogue data for the "NPC" we just created.
                            # I reckon we can give dialogue data to an indicator arrow, if we really want to...
                            self.master_plane.entities[genus][-1].load_conversation_data_from_node(dialogue_node)#session)


                elif (genus == GENUS_GOLD):

                    # Give each piece of a gold a unique name
                    uid = len(self.master_plane.entities[genus])

                    self.master_plane.entities[genus].append(
                        Gold().describe(
                            ref_entity.get_attributes()
                        ).customize(
                            ref_entity.get_attributes()
                        )
                    )

                    gold = self.master_plane.entities[genus][-1]

                    """ Note - Removed autonaming on map load, moved it to create entity method """
                    #if (gold.name == ""):
                    #    gold.name = "gold.uid.%d" % uid

                elif (genus == GENUS_LEVER):

                    self.master_plane.entities[genus].append(
                        Lever().describe(
                            ref_entity.get_attributes()
                        ).customize(
                            ref_entity.get_attributes()
                        )
                    )


        # After loading the entities, make sure that every enemy object
        # has a name.  Without a name, AI state synchronization can
        # terribly fail in netplay mode.  (We should never have an unnamed enemy,
        # but sometimes the level designer doesn't get it right!)
        enemies = self.get_entities_by_type(GENUS_ENEMY)
        for i in range( 0, len(enemies) ):

            # Convenience
            e = enemies[i]

            # Empty string for name?
            if ( e.get_name() == "" ):

                # Give a generated name
                e.set_name( "unnamed%s" % i )


        # Having loaded in all gold entities, we can build the master plane's gold cache...
        self.master_plane.build_gold_cache()

        #log( "Loaded entities / gold in %s seconds" % (time.time() - a) )
        #a = time.time()


        # Check for triggers section
        ref_triggers = map_node.find_node_by_tag("triggers")

        # Validate
        if (ref_triggers):

            # Loop triggers
            for ref_trigger in ref_triggers.get_nodes_by_tag("trigger"):

                # Load from XML
                self.triggers.append(
                    Trigger().configure(
                        ref_trigger.get_attributes()
                    ).setup_events_from_node( ref_trigger )
                )


        # Load in any scripts...
        ref_scripts = map_node.find_node_by_tag("scripts")

        # Validate
        if (ref_scripts):

            # Loop results
            for ref_script in ref_scripts.get_nodes_by_tag("script"):

                # Each node contains a block of script text.
                # Store it in this map's scripts hash, keyed by the script name.
                self.scripts[ ref_script.attributes["name"] ] = ref_script.innerText

                # Save the script's name to the preferred script order list
                self.preferred_script_order.append( ref_script.attributes["name"] )


        #log( "Processed miscellaneous data in %s seconds" % (time.time() - a) )
        #a = time.time()


        #log( "Processed additional miscellaneous data in %s seconds" % (time.time() - a) )
        #a = time.time()


        """ (moved to universe.activate_map_on_layer_by_name or whatever I'm calling it now)
        # Does the map have an onload script?
        if ( ( not options["is-editor"] ) and ( "onload" in self.scripts ) ):

            # The onload script is typically just a bunch of flag settings and such,
            # so we make sure to run through everything we can immediately...
            self.run_script("onload", control_center, universe, execute_all = True)#network_controller, universe, session, quests, execute_all = True)
        """


        #log( "Considered 'onload' in %s seconds" % (time.time() - a) )
        #a = time.time()


        # Update map dimensions
        self.update_dimensions()

        # Default to the first plane
        self.active_plane_z_index = 0

        #log( "Completed final map.load processing in %s seconds" % (time.time() - a) )

    def save(self, path):

        data = self.compile_save_string()

        f = open(path, "w")
        f.write(data)
        f.close()

        self.saved = True
        self.modified = False

    def compile_save_string(self, prefix = ""):

        xml = ""

        # Save generic map params
        xml += "%s<params>\n" % prefix

        xml += "%s\t<param key = '%s' value = '%s' />\n" % (prefix, xml_encode( "layer" ), xml_encode( "%s" % self.layer ) )
        xml += "%s\t<param key = '%s' value = '%s' />\n" % (prefix, xml_encode( "type" ), xml_encode( "%s" % self.get_param("type") ) )

        # Optional params
        for key in ("next-map", "overview"):

            # Check for map param
            if ( self.get_param(key) ):

                # Add param
                xml += "%s\t<param key = '%s' value = '%s' />\n" % ( prefix, xml_encode( "%s" % key ), xml_encode( "%s" % self.get_param(key) ) )

        xml += "%s</params>\n" % prefix


        # Save planes
        xml += "%s<planes>\n" % prefix

        for plane in self.planes:
            xml += plane.compile_xml_string(prefix + "\t")

        xml += "%s</planes>\n" % prefix


        # Save entities
        xml += "%s<entities>\n" % prefix

        for genus in self.master_plane.entities:

            for e in self.master_plane.entities[genus]:
                xml += e.compile_xml_string(prefix + "\t")

        xml += "%s</entities>\n" % prefix


        # Save triggers
        xml += "%s<triggers>\n" % prefix

        for t in self.triggers:
            xml += t.compile_xml_string(prefix + "\t")

        xml += "%s</triggers>\n" % prefix


        # Save scripts
        ref_scripts = XMLNode("scripts")

        # I prefer to save the scripts in the same order I loaded them.
        # I do have to save them all, though, so let's add in new scripts...
        for name in sorted( self.scripts.keys() ):

            # Perhaps we created this one after the initial load...
            if ( not (name in self.preferred_script_order) ):

                # Append to the end
                self.preferred_script_order.append(name)


        # Loop scripts on this map
        for name in self.preferred_script_order:

            # Add script node
            node = ref_scripts.add_node(
                XMLNode("script").set_attributes({
                    "name": xml_encode(name)
                })
            )

            # Set inner text as the script data
            node.set_inner_text(
                xml_encode(
                    self.scripts[name]
                )
            )


        # Compile the xml and add it to the xml
        xml += ref_scripts.compile_xml_string()
        """
        xml += "%s<scripts>\n" % prefix

        for key in self.scripts:
            xml += "%s\t<script name = '%s'>%s</script>\n" % (prefix, key, xml_encode(self.scripts[key]))#self.scripts[key].compile_xml_string(prefix + "\t")

        xml += "%s</scripts>\n" % prefix
        """


        return xml

    def save_memory(self, universe):

        # We don't save memory data for challenge maps...
        if ( self.get_type() == "challenge" ):
            return

        # Or puzzle maps...
        elif ( self.get_type() == "puzzle" ):
            return

        else:

            path = os.path.join( universe.get_working_save_data_path(), "active", "history")

            # Make sure the path exists
            ensure_path_exists(path)

            # Compile a memory string
            xml = self.save_state().compile_inner_xml_string() # Whatever, bad design from the start

            # Save to file
            f = open( os.path.join(path, "%s.history.xml" % self.name), "w" )
            f.write(xml)
            f.close()


    def save_state(self):

        # Create root node
        root = XMLNode("map")


        # First, let's track some miscellaneous parameters
        node = root.add_node(
            XMLNode("params")
        )

        # Loop a few keys...
        for key in ("stats.enemies-killed", "stats.bombs-used", "stats.skills-used"):

            # Add a node for each param
            node.add_node(
                XMLNode(key).set_inner_text(
                    "%d" % self.get_param(key)
                )
            )


        # Start with entities
        node = root.add_node(
            XMLNode("entities")
        )

        # Loop each genus
        for genus in self.master_plane.entities:

            # Loop entities of current genus
            for entity in self.master_plane.entities[genus]:

                # We don't care about ghost entities (e.g. hologram) or disposable entities
                if ( (not entity.is_ghost) and (not entity.is_ghost) ):

                    # Add node
                    node.add_node(
                        entity.save_state()
                    )
                    #xml += entity.compile_memory_string("\t")

        # Create triggers node
        node = root.add_node(
            XMLNode("triggers")
        )

        # Loop triggers
        for trigger in self.triggers:

            # Save state
            node.add_node(
                trigger.save_state()
            )


        # Create planes node
        node = root.add_node(
            XMLNode("planes")
        )

        # Loop planes
        for plane in self.planes:

            # Save state
            node.add_node(
                plane.save_state()
            )


        # Add in dig state data from the master plane
        root.add_node(
            self.master_plane.save_dig_state()
        )


        # Add in ai state data from the master plane
        root.add_node(
            self.master_plane.save_ai_state()
        )


        # Create a node to track conversation state data.
        # No, I don't know why I didn't put this in with the actual entities.
        node = root.add_node(
            XMLNode("conversations")
        )

        # Loop NPC entities
        for npc in self.master_plane.entities[GENUS_NPC]:

            # Create a node for the NPC
            node2 = node.add_node(
                XMLNode("npc").set_attributes({
                    "name": xml_encode( "%s" % npc.name )
                })
            )

            # Loop NPC's conversations
            for conversation_id in npc.conversations:

                # Save state
                node2.add_node(
                    npc.conversations[conversation_id].save_state()
                )


        # Return map state node
        return root


    def load_memory(self, universe, session = None):

        path = os.path.join( universe.get_working_save_data_path(), "active", "history", "%s.history.xml" % self.name )

        if (os.path.exists(path)):

            # Read data
            f = open(path, "r")
            xml = f.read()
            f.close()

            # I never used <map> container node, so I'm going to hack it in here.  Don't laugh.
            xml = "<map>%s</map>" % xml

            # Parse xml
            node = XMLParser().create_node_from_xml(xml).find_node_by_tag("map")

            # Load map state
            self.load_state(node)


    # Load map state
    def load_state(self, node):

        # Load in params data
        ref_params = node.find_node_by_tag("params")

        # Validate
        if (ref_params):

            # Check for some miscellaneous params...
            for key in ("stats.enemies-killed", "stats.bombs-used", "stats.skills-used"):

                # We save these using the key as a tag name
                ref = ref_params.find_node_by_tag(key)

                # Validate
                if (ref):

                    # These are all numeric values.  Read in the inner text as a numeric value
                    self.set_param(
                        key,
                        int( ref.innerText )
                    )


        # Load in entity data
        ref_entities = node.find_node_by_tag("entities")

        # Validate
        if (ref_entities):

            # Loop each entity's state
            for ref_entity in ref_entities.get_nodes_by_tag("entity"):

                # Find entity
                entity = self.get_entity_by_name( ref_entity.get_attribute("name") )

                # Validate
                if (entity):

                    # Load state
                    entity.load_state(ref_entity)


        # Load in trigger data
        ref_triggers = node.find_node_by_tag("triggers")

        # Validate
        if (ref_triggers):

            # Loop trigger states
            for ref_trigger in ref_triggers.get_nodes_by_tag("trigger"):

                # Find trigger
                trigger = self.get_trigger_by_name( ref_trigger.get_attribute("name") )

                # Validate
                if (trigger):

                    # Load trigger state
                    trigger.load_state(ref_trigger)


        # Load in planar data
        ref_planes = node.find_node_by_tag("planes")

        # Validate
        if (ref_planes):

            # Loop plane states
            for ref_plane in ref_planes.get_nodes_by_tag("plane"):

                # Find plane
                plane = self.get_plane_by_name( ref_plane.get_attribute("name") )

                # Validate
                if (plane):

                    # Ignore modal planes, which do not use state data (e.g. mask layer)
                    if (not plane.is_modal):

                        # Remove the plane from the map for a moment
                        self.remove_plane_from_master_plane(plane)

                        # Load plane state
                        plane.load_state(ref_plane)

                        # Merge the plane back into the master plane
                        self.merge_plane_into_master_plane(plane)

                else:
                    log( "Warning:  Plane '%s' does not exist!" % ref_plane.get_attribute("name") )


        # Before loading dig state data, let's
        # quickly reset any existing dig state data on the master plane.
        self.master_plane.reset_dig_data()


        # Note - For now, I'm disabling dig memory data.  It annoys more than anything...
        """
        # Load in dig state data
        ref_digs = node.get_first_node_by_tag("digs")

        # Validate
        if (ref_digs):

            log( "let's recall dig memory..." )
            log( ref_digs.get_nodes_by_tag("dig") )

            # Tell the master plane to remember the dig data
            self.master_plane.load_dig_state(ref_digs)# ref_digs.get_nodes_by_tag("dig") )
        """


        # Load in AI state data
        ref_ai = node.get_first_node_by_tag("ai")

        # Validate
        if (ref_ai):

            self.master_plane.load_ai_state(ref_ai, self)



        # Load in conversation data
        ref_conversations = node.get_nodes_by_tag("conversations")

        if (len(ref_conversations) > 0):

            npc_collection = ref_conversations[0].get_nodes_by_tag("npc")

            for ref_npc in npc_collection:

                log( "npc:  ", ref_npc.get_attribute("name") )

                for zz in self.master_plane.entities[GENUS_NPC]:
                    log( "npc found:  ", zz.name )

                # Reference to the NPC for whom we'll be loading conversation data memory...
                entity = self.get_entity_by_name( ref_npc.get_attribute("name") )


                conversation_collection = ref_npc.get_nodes_by_tag("conversation")

                for ref_conversation in conversation_collection:

                    # Get conversation id
                    conversation_id = ref_conversation.get_attribute("id")
                    log( ref_conversation.get_attribute("id") )

                    # Validate
                    if (conversation_id in entity.conversations):

                        # Load conversation state
                        entity.conversations[conversation_id].load_state(ref_conversation)


        # In case we need to account for previously-moved planes...
        self.update_master_plane()

        # Rebuild the gold cache
        self.master_plane.build_gold_cache()


    # Get a handle to this map's parent universe
    def get_parent(self):

        # Return
        return self.parent


    # Get the map name
    def get_name(self):

        # Return
        return self.name


    # Get the map title
    def get_title(self):

        # Return
        return self.title


    # Get the map type (just a param)
    def get_type(self):

        # Return type param
        return self.get_param("type")


    # Set the map type (typically done within level file, but done explicitly for GIFs, etc.)
    def set_type(self, value):

        # Update type
        self.set_param("type", value)


    # Set map status (cutscene, active, etc.)
    def set_status(self, status):

        self.status = status


    # Get map status.  Implicitly returns cutscene status if cutscene counter is greater than 0.
    def get_status(self):

        # Cutscene counter check
        if (self.cutscene_counter > 0):

            return STATUS_CUTSCENE

        else:

            return self.status


    # Reset the completion timer (count in frames)
    def reset_completion_time(self):

        # Back to 0
        self.completion_time = 0


    # Get completion timer value (count in frames)
    def get_completion_time(self):

        # Return
        return self.completion_time


    # Turn on cutscene mode (increment counter)
    def cutscene_on(self):

        # Increment
        self.cutscene_counter += 1


    # Turn off cutscene mode (lower counter)
    def cutscene_off(self):

        # Decrement
        self.cutscene_counter -= 1


        # Stay non-negative
        if (self.cutscene_counter <= 0):

            # Clamp
            self.cutscene_counter = 0


        # Return True if the cutscene is over now
        return (self.cutscene_counter == 0)


    # Get map width (in pixels)
    def get_width_in_pixels(self):

        return ( self.master_plane.tiles.get_width() * TILE_WIDTH )


    # Get map height (in pixels)
    def get_height_in_pixels(self):

        return ( self.master_plane.tiles.get_height() * TILE_HEIGHT )


    # Check if this map redlines (simple param check)
    def is_redlined(self):

        # Check to see if it's a 0 or a 1
        return ( int( self.get_param("redline") ) == 1 )


    # Set fall regions.  Expects a list.
    def set_fall_regions(self, regions):

        # Set
        self.fall_regions.extend(regions)


    # Get all fall regsions
    def get_fall_regions(self):

        # Return
        return self.fall_regions


    def set_status_message(self, message):

        self.status_message = message


    # Set multiple map parameters.  Accepts a hash.
    def set_params(self, params):

        # Set each param
        for key in params:

            # Update
            self.set_param(key, params[key])


    # Set a map parameter
    def set_param(self, param, value):

        # Validate
        if (1):#param in self.params):

            # Set
            self.params[param] = value


    # Attempt to retrieve a given map parameter
    def get_param(self, param):

        # Validate
        if (param in self.params):

            return self.params[param]

        # Not found
        else:

            log2( "Warning:  Map param '%s' does not exist!" % param )
            return None


    # Get the map's wave tracker
    def get_wave_tracker(self):

        return self.wave_tracker


    # Reset the map's wave tracker for a new wave
    def reset_wave_tracker(self):

        # Simply replace it with a clean, default wave tracker
        self.wave_tracker = WaveTracker()


    # Get the event controller
    def get_event_controller(self):

        # Return
        return self.event_controller


    # Check to see if a script by a given name exists
    def does_script_exist(self, name):

        return (name in self.scripts)


    # Import a script, given a key and script data
    def import_script(self, name, data):

        # Validate that we have data to import
        if (data != None):

            # Save script
            self.scripts[name] = data


    # Run a script, by name
    def run_script(self, name, control_center, universe, execute_all = False):

        log2( "Run script:  '%s'" % name )

        # Validate
        if ( self.does_script_exist(name) ):

            # Do we need to compile this script?
            if ( not (name in self.compiled_scripts) ):

                # Compile on-the-fly
                self.compiled_scripts[name] = Script( self.scripts[name] )


            # Load the compiled script
            self.event_controller.load(#load_packets_from_xml_node( self.scripts[name] )
                self.compiled_scripts[name]
            )

            #print name, self.scripts[name]
            #print self.scripts[name].compile_xml_string()

            # For some scripts (e.g. onload), we want to run as many events as possible...
            if (execute_all):

                self.event_controller.loop(control_center, universe)#, self, session, quests)


    # Execute a script immediately, by name.
    # Any blocking call will fail!
    def execute_script(self, name, control_center, universe, execute_all = False):

        # Validate
        if ( self.does_script_exist(name) ):

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


    def is_busy(self):

        if (self.level_menu):

            return (self.level_menu.is_dismissed == False)

        else:

            return False


    # Get active particles
    def get_particles(self):

        # Return all
        return self.particles


    def randomize_base_tile(self, tile, randomizer_range):

        for plane in self.planes:

            plane.randomize_base_tile(tile, randomizer_range)


    # Center a given camera object on a given entity (by entity name)
    def center_camera_on_entity_by_name(self, camera, name, zap = False):

        # Zap the camera onto the entity
        entity = self.get_entity_by_name(name)

        # Assuming we found that entity...
        if (entity):

            # Focus the camera on the entity
            camera.focus(entity, self)

            # Immediate camera positioning?
            if (zap):

                camera.zap()


    # Center a given camera on this map
    def center_within_camera(self, camera, scale = 1):

        # Position the camera such that this map appears centered...
        camera.position(
            x = (self.x * TILE_WIDTH) + int( ( (self.width * TILE_WIDTH) - camera.get_width() ) / 2 ),
            y = (self.y * TILE_HEIGHT) + int( ( (self.height * TILE_HEIGHT) - camera.get_height() ) / 2 )
        )

        #log2( "camera:", (camera.x, camera.y) )


    # Center a given camera on this map, using parallax...
    def center_within_camera_using_parallax(self, camera):

        # Map universal position, scaled
        (x, y) = (
            int( ((self.x * TILE_WIDTH) * BACKGROUND_MAP_SCALE) / BACKGROUND_MAP_PARALLAX_SCALE ),
            int( ((self.y * TILE_HEIGHT) * BACKGROUND_MAP_SCALE) / BACKGROUND_MAP_PARALLAX_SCALE )
        )

        # Map dimensions, scaled
        (w, h) = (
            int( (self.width * TILE_WIDTH) * BACKGROUND_MAP_SCALE ),
            int( (self.height * TILE_HEIGHT) * BACKGROUND_MAP_SCALE )
        )

        # Position the camera such that this map appears centered...
        camera.position(
            x = (x + int(w / 2)) - int( camera.get_width() / 2 ),
            y = (y + int(h / 2)) - int( camera.get_height() / 2 )
        )
        #    x = int( int( (self.x * TILE_WIDTH) + int( ( (self.width * TILE_WIDTH) - camera.get_width() ) / 2 ) * BACKGROUND_MAP_SCALE ) / BACKGROUND_MAP_PARALLAX_SCALE ),
        #    y = int( int( (self.y * TILE_HEIGHT) + int( ( (self.height * TILE_HEIGHT) - camera.get_height() ) / 2 ) * BACKGROUND_MAP_SCALE ) / BACKGROUND_MAP_PARALLAX_SCALE )
        #)

        log2( "camera parallax:", (camera.x, camera.y) )


    def create_hack_panel(self, passcode):
        self.hack_panel = HackPanel(passcode)

    def create_dialogue_panel(self, line, universe, session, quests, conversation, entity, event_type = None, shop = False):

        # This function is obsolete.
        log2( "Warning:  Do not use function create_dialogue_panel." )
        return

        """
        # Does the line have any pre-script data that we should try to process?
        if (line.pre_script):

            # I want to handle these events immediately.  You can't use blocking events (successfully) in a pre-script...
            controller = EventController()

            controller.load_packets_from_xml_node(line.pre_script)


            # Run for as long as possible.  You can only inject simple single-use events...
            result = controller.process(universe, self, session, quests)

            while (result == True):
                result = controller.process(universe, self, session, quests)


        # Create a shopping dialogue panel?
        if (event_type == EVENT_TYPE_DIALOGUE_SHOP):

            self.dialogue_panel = DialoguePanelShop(line, universe, session, conversation, entity, event_type)

        # Create a computer dialogue panel?
        elif (event_type == EVENT_TYPE_DIALOGUE_COMPUTER):

            # Here we must make a choice.  If none of the responses has "details" (e.g. e-mail etc.), then
            # we're going to fall back to a simple RowMenu-ish version of the dialogue.
            if ( 1 or all( o.details == "" for o in line.responses ) ):

                self.dialogue_panel = DialoguePanelComputerSimple(line, universe, session, conversation, entity, event_type)

            # Otherwise, we'll show a full-fledged "computer" dialogue panel
            else:

                self.dialogue_panel = DialoguePanelComputer(line, universe, session, conversation, entity, event_type)

        # Nope, just an ordinary dialogue panel...
        else:

            self.dialogue_panel = DialoguePanel(line, universe, session, conversation, entity, event_type)
        """



    # Some challenge maps will rotate pieces of gold on/off as the
    # player collects gold.  This function disables all but n pieces of gold in preparation.
    def prepare_gold_rotation(self, control_center, universe):

        # First, let's disable all gold
        self.disable_all_gold_pieces(control_center, universe)


        # If this map defines and uses a gold rotation size param, then let's deactivate all of the gold on the map
        # before selecting N at random to begin as active...
        size = int( self.get_wave_tracker().get_wave_param("gold-rotation-size") )

        # Only run this logic for positive parameters
        if (size > 0):

            # Mark all of the gold as collected by default
            gold_collection = self.get_entities_by_type(GENUS_GOLD)

            # Iterate
            for gold in gold_collection:

                # Hide it
                gold.collected = True


            # Now, prepare to choose N at random to be active...
            eligible = []

            # At first, add all to our list...
            for i in range(0, len(gold_collection)):

                # Everyone has a chance
                eligible.append(i)

            # Track how many gold bars we've activated so far...
            counter = 0

            while ( (counter < size) and (len(eligible) > 0) ):

                # Pick a random index to activate
                winner = random.randint( 0, len(eligible) - 1 )

                # Activate it!
                gold_collection[ eligible.pop(winner) ].queue_for_reactivation()


                # Increment counter
                counter += 1

        #self.activate_random_gold_piece_in_collection(gold_collection)
        # Also create a dead enemy; he will respawn immediately on one of the challenge room's respawn points...
        #self.create_random_enemy()
            

    def activate_random_gold_piece_in_collection(self, gold_collection, exception = None):

        # This should never happen, but just in case...
        if ( len(gold_collection) <= 3 ):

            log2( "Warning:  Less than 3 gold pieces found on the map, skipping random activation..." )
            return

        # If none of the (non-excepted) gold in the collection is marked as collected, then there's nothing to activate.
        elif ( all( (not gold.collected) or (gold == exception) for gold in gold_collection ) ):

            return

        else:

            index = random.randint(0, len(gold_collection) - 1)

            # We don't want to pick the same one twice consecutively, probably...
            while ( (gold_collection[index] == exception) or (not gold_collection[index].collected) ):
                index = random.randint(0, len(gold_collection) - 1)


            gold_collection[index].queue_for_reactivation()#collected = False


    # Enable all gold on the map
    def enable_all_gold_pieces(self, control_center, universe):

        # Loop
        for gold in self.get_entities_by_type(GENUS_GOLD):

            # Queue for reactivation (?)
            gold.queue_for_reactivation()


    # Disable all gold on the map
    def disable_all_gold_pieces(self, control_center, universe):

        # Loop
        for gold in self.get_entities_by_type(GENUS_GOLD):

            # Disable
            gold.disable(control_center, universe)


    # How many uncollected gold bars remain?
    def remaining_gold_count(self, region = None):

        count = 0

        gold_collection = self.get_entities_by_type(GENUS_GOLD)

        for gold in gold_collection:

            if (not gold.collected):

                # Limit by region?
                if (region):

                    if ( intersect(region, gold.get_rect()) ):

                        count += 1

                # Nope; count them all...
                else:
                    count += 1

        return count

    # How many gold bars have been collected?
    def collected_gold_count(self, region = None):

        count = 0

        gold_collection = self.get_entities_by_type(GENUS_GOLD)

        for gold in gold_collection:

            if (gold.collected):

                # Limit by region?
                if (region):

                    if ( intersect(region, gold.get_rect()) ):

                        count += 1

                # Nope; count them all...
                else:
                    count += 1

        return count

    # Total gold originally available in level...
    def get_gold_count(self, region = None):

        if (region):

            count = 0

            gold_collection = self.get_entities_by_type(GENUS_GOLD)

            for gold in gold_collection:

                if ( intersect(region, gold.get_rect()) ):

                    count += 1

            return count

        else:

            # Irregardless of collection status, fetch original amount...
            return ( len(self.master_plane.entities[GENUS_GOLD]) )


    # Advance to the next challenge wave, tracking the wave number as a map param
    # and spawning a new enemy, plus adding newsfeeder data and providing new bombs for the player(s).
    def next_challenge_wave(self):

        # Increment param
        self.set_param(
            "wave",
            "%d" % (1 + int( self.get_param("wave") ))
        )

        # Add another bad guy...
        enemy = self.create_random_enemy()

        # Validate
        if (enemy):
            pass


        # **Add new bombs

        # **Add newsfeeder:  WAVE n, BOMBS ADDED: n

        # **Add coop survival maps!!!!!!!


    def create_player(self):

        return Player()


    def create_random_enemy(self, is_disposable = False, name = ""):

        for i in range(0, 1):

            # Make sure we have room for a new enemy
            if ( len(self.master_plane.entities[GENUS_ENEMY]) < MAX_ENEMY_COUNT ):

                e = Enemy()

                e.name = name

                e.is_disposable = is_disposable
                e.is_ghost = True

                e.alive = False
                e.respawn_interval = 1

                self.master_plane.entities[GENUS_ENEMY].append(e)

                e.alive = False
                e.set_status(STATUS_INACTIVE)
                e.ai_state.ai_respawn_interval = 0
                e.respawn()

                return e

            # Otherwise, abort...
            else:

                return None


    # Kill all enemies on the current map, but don't remove them.
    # Let them respawn normally, if/a.
    def kill_enemies(self, control_center, universe):

        # Loop all active enemies.
        # No point in killing one that's already dead.
        for entity in self.get_active_entities_by_type(GENUS_ENEMY):

            # Kill normally
            entity.die(DEATH_BY_VAPORIZATION, control_center, universe)


    # Kill only those enemies that are carrying gold
    def kill_enemies_with_gold(self, control_center, universe):

        # Loop all active enemies.
        # No point in killing one that's already dead.
        for entity in self.get_active_entities_by_type(GENUS_ENEMY):

            # Carrying gold?
            if (entity.ai_state.ai_is_carrying_gold):

                # Kill normally
                entity.die(DEATH_BY_VAPORIZATION, control_center, universe)


    # Remove any random enemy (i.e. dynamically created via script) from the map.
    def remove_random_enemies(self, control_center, universe):

        # Loop all enemies
        for entity in self.get_entities_by_type(GENUS_ENEMY):

            # See if it's a transient enemy
            if (entity.is_ghost):

                # Kill and corpse
                entity.die(DEATH_BY_VAPORIZATION, control_center, universe)

                # Mark as corpsed
                entity.corpsed = True


    # Scale current speed for all enemies on this map
    def scale_enemies_speed(self, scale):

        # Loop enemies
        for e in self.get_entities_by_type(GENUS_ENEMY):

            # Scale
            e.set_speed(
                scale * e.get_base_speed()
            )


    def create_bomb_with_unique_id(self, x, y):

        # counter
        counter = 1


        # Generate a unique id
        name = "bomb%d" % counter

        # Ensure it's unique
        while ( self.get_entity_by_name(name) ):

            # Next!
            counter += 1

            # Try again
            name = "bomb%d" % counter


        # Now we have our distinct id...
        bomb = self.add_entity_by_type(GENUS_BOMB, "", name, None)


        # Update position
        bomb.set_x(x)
        bomb.set_y(y)


        # Return the new bomb
        return bomb


    def record_obituary(self, entity_name, universe):

        path = os.path.join( universe.get_working_save_data_path(), "active" )

        ensure_path_exists(path)

        obit_path = os.path.join(path, "obituaries.xml")

        xml = "<entity map = '%s' name = '%s' />\n" % (self.name, entity_name)

        f = open(obit_path, "a")
        f.write(xml)
        f.close()


    def count_living_enemies(self):

        count = 0

        for enemy in self.master_plane.entities[GENUS_ENEMY]:

            if ( (not enemy.alive) and (enemy.corpsed) ):

                pass

            else:

                count += 1

        return count


    def get_packet_node(self, script, index):

        if (script in self.scripts):

            nodes = self.scripts[script].get_nodes_by_tag("packet")

            if (index < len(nodes)):
                return nodes[index]

        return None


    def get_relative_rect(self, sCoords = None):

        if (sCoords):
            return( (self.x - sCoords[0]) * TILE_WIDTH, (self.y - sCoords[1]) * TILE_HEIGHT, (self.width * TILE_WIDTH), (self.height * TILE_HEIGHT) )

        else:
            return (0, 0, (self.width * TILE_WIDTH), (self.height * TILE_HEIGHT))


    # Get all triggers on this map
    def get_triggers(self):

        # Return
        return self.triggers


    # Get a trigger by a given name
    def get_trigger_by_name(self, name):

        for t in self.triggers:

            if (t.name == name):
                return t

        # We couldn't find that trigger...
        return None


    # Delete a trigger by a given name
    def delete_trigger_by_name(self, name):

        i = 0

        while (i < len(self.triggers)):

            if (self.triggers[i].name == name):
                self.triggers.pop(i)

            else:
                i += 1


    def send_message_to_trigger(self, trigger, entity_name, message, param, universe):#, p_map, session):

        # Forward the message
        trigger.handle_message("unused", entity_name, message, param, universe)#, p_map, session)


    def get_active_plane(self):

        for plane in self.planes:

            if (plane.z_index == self.active_plane_z_index):
                return plane

        return None


    def add_entity_by_type(self, entity_type, entity_species, entity_name, entity_ai_behavior):

        e = None

        if (entity_type == GENUS_PLAYER):

            e = Player()

        elif (entity_type == GENUS_ENEMY):

            e = Enemy()
            e.ai_state.ai_behavior = entity_ai_behavior

        elif (entity_type == GENUS_RESPAWN_ENEMY):

            e = EnemyRespawn()

        elif (entity_type == GENUS_NPC):

            if (entity_species == "generic"):
                e = NPC()

            elif (entity_species == "terminal"):
                e = Terminal()

            elif (entity_species == "indicator-arrow"):
                e = IndicatorArrow()

        elif (entity_type == GENUS_GOLD):

            # Create a Gold entity
            e = Gold()

            # Autoname the piece of gold with a unique id
            i = 1
            while ( self.get_entity_by_name("gold%d" % i) != None ):

                # We want a unique id
                i += 1

            # Set gold name
            e.set_name("gold%d" % i)

            # Add new gold entity
            self.master_plane.entities[entity_type].append(e)

            # Return new gold
            return e

        elif (entity_type == GENUS_LEVER):

            e = Lever()

        elif (entity_type == GENUS_BOMB):

            e = Bomb()

        elif (entity_type == GENUS_RESPAWN_PLAYER):

            e = PlayerRespawn()

            e.set_status(STATUS_ACTIVE)

        else:
            log( "Unknown entity type '%d'" % entity_type )


        if (e):
            e.name = entity_name

            self.master_plane.entities[entity_type].append(e)
            return self.master_plane.entities[entity_type][-1]


    # Remove an entity by a given name.  Does nothing if the entity does not exist.
    def remove_entity_by_name(self, name):

        # Check each genus
        for genus in self.master_plane.entities:

            # Loop entities of this type
            i = 0
            while ( i < len(self.master_plane.entities[genus]) ):

                # Match?
                if ( self.master_plane.entities[genus][i].name == name ):

                    # Later!
                    self.master_plane.entities[genus].pop(i)

                else:
                    i += 1


    def remove_entity_by_type_and_name(self, entity_type, name):

        i = 0
        while (i < len(self.master_plane.entities[entity_type])):

            if (self.master_plane.entities[entity_type][i].name == name):
                self.master_plane.entities[entity_type].pop(i)

            else:
                i += 1


    def get_entity_index(self, entity):

        for genus in self.master_plane.entities:

            for i in range(0, len(self.master_plane.entities[genus])):

                if (self.master_plane.entities[genus][i] == entity):
                    return i

        return -1


    def get_entity_by_type_and_index(self, entity_type, index):
        return self.master_plane.entities[entity_type][index]


    def get_entity_by_name(self, name):

        return self.master_plane.get_entity_by_name(name)


    def get_entities_by_type(self, genus):

        return self.master_plane.entities[genus]


    # Get all entities at a given tile location (used only for level editing, currently)
    def get_entities_at_tile_coords(self, tx, ty):

        # Track results
        results = []

        # Loop genus
        for genus in self.master_plane.entities:

            # Loop entities
            for entity in self.master_plane.entities[genus]:

                # Only exact matches, for now, which is fine for the level editor...
                if ( (entity.x == (tx * TILE_WIDTH)) and (entity.y == (ty * TILE_HEIGHT)) ):

                    # Add match
                    results.append(entity)

        # Return rsults
        return results


    # Delete all entities at a given tile location (used only for level editing)
    def delete_entities_at_tile_coords(self, tx, ty):

        # Get all entities at the given tile coords
        entities = self.get_entities_at_tile_coords(tx, ty)

        # Remove all
        while ( len(entities) > 0 ):

            # Next
            entity = entities.pop()

            # Removme entity
            self.delete_entity(entity)


    # Delete a given entity object (level editing)
    def delete_entity(self, entity):

        # Loop genus
        for genus in self.master_plane.entities:

            # Loop all entities in genus
            i = 0
            while ( i < len(self.master_plane.entities[genus]) ):

                # Match?
                if ( self.master_plane.entities[genus][i] == entity ):

                    # Remove
                    self.master_plane.entities[genus].pop(i)

                else:
                    i += 1


    def spotlight_entity_by_type(self, target_entity, genus):

        self.master_plane.spotlight_entity_by_type(target_entity, genus)

    def get_active_entities_by_type(self, genus):

        results = []

        for entity in self.get_entities_by_type(genus):

            if ( entity.get_status() == STATUS_ACTIVE ):

                results.append(entity)

        return results


    # Count the number of enemies in a given region
    def count_enemies_in_rect(self, r, exceptions = []):

        # Return count
        return self.master_plane.count_enemies_in_rect(r, exceptions)


    def count_entities_in_rect(self, r, exceptions = []):

        return self.master_plane.count_entities_in_rect(r, exceptions)


    # Forward on to the master plane; it has all of the entity data...
    def query_interentity_collision_for_entity(self, ref_entity):

        return self.master_plane.query_interentity_collision_for_entity(ref_entity)


    # Forward on to the master plane...
    def query_interentity_collision_for_entity_against_entity_types(self, entity_types, ref_entity):

        return self.master_plane.query_interentity_collision_for_entity_against_entity_types(entity_types, ref_entity)


    def get_bombable_entities(self):

        results = []

        for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

            for entity in self.master_plane.entities[genus]:

                # Only return living entities.  If they're already dead, how can they die again?  It'd
                # lead to annoying recursion crashes...
                if (entity.status == STATUS_ACTIVE):

                    results.append(entity)

        return results


    # Create a new plane object.
    # Does not add it to the map's planes list.
    def create_plane(self):

        # Create new plane object
        plane = Plane()

        # Give the new plane a handle to this map's parent universe's
        # tilesheet collision values.
        plane.set_collision_values(
            self.get_parent().get_collision_values()
        )

        # Return the new plane object
        return plane


    # Add a new plane to this map
    def add_plane(self, plane):

        # Add to list of plane objects
        self.planes.append(plane)

        # Give the plane a handle to this map's parent universe's
        # tilesheet collision values.
        plane.set_collision_values(
            self.get_parent().get_collision_values()
        )


    # Used for level editor only
    def update_plane_z_indices(self):

        # Add each plane and its z-index... put the z-index first...
        planes_by_z_index = []

        for plane in self.planes:
            planes_by_z_index.append( (plane.z_index, plane) )

        # Now sort the list...
        planes_by_z_index.sort()

        # Now loop through and update...
        for i in range(0, len(planes_by_z_index)):

            (z_index, plane) = (i, planes_by_z_index[i][1])
            plane.z_index = z_index


    def update_dimensions(self):

        w = 0

        # Offset by each plane's relative coordinates, we can use the the maximum such width
        # to determine the overall width of the map.
        for p in self.planes:
            max_x = (p.x) + p.get_width()

            if (max_x > w):
                w = max_x

        self.width = w


        h = 0

        # Same tale
        for p in self.planes:
            max_y = (p.y) + p.get_height()

            if (max_y > h):
                h = max_y

        self.height = h

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def build_master_plane(self, planes):

        master_plane = self.create_plane()

        # First I want to calculate the overall dimensions I'll need to
        # encompass all of the planes
        w = 0
        h = 0

        for plane in planes:

            lx = plane.x
            ly = plane.y

            lw = plane.tiles.get_width()
            lh = plane.tiles.get_height()

            if ( (lx + lw) > w ):
                w = (lx + lw)

            if ( (ly + lh) > h ):
                h = (ly  + lh)


        # Clear the master plane
        master_plane.tiles.clear()
        master_plane.tiles_backup.clear()

        master_plane.traps.clear()

        # Loop all planes, importing data from bottom to top
        for plane in planes:

            # The master plane will ignore modal (mask) planes during import...
            if (not plane.is_modal):

                # Offset information
                lx = plane.x + plane.shift_x
                ly = plane.y + plane.shift_y

                # Loop all tiles in the current plane
                for y in range( 0, plane.tiles.get_height() ):
                    for x in range( 0, plane.tiles.get_width() ):

                        # Get coordinates on master plane
                        (tx, ty) = (
                            (lx + x),
                            (ly + y)
                        )

                        # Don't overwrite a lower plane's tile data unless this plane
                        # has a tile in that position as well.
                        if (
                            ( master_plane.tiles.read(tx, ty) == 0 ) or
                            ( plane.tiles.read(x, y) > 0 )
                        ):

                            master_plane.tiles.write( tx, ty, plane.tiles.read(x, y) )
                            master_plane.tiles_backup.write( tx, ty, plane.tiles.read(x, y) )

        # Write an empty Trap object for each tile on the master plane
        for y in range( 0, master_plane.get_height() ):
            for x in range( 0, master_plane.get_width() ):

                master_plane.traps.write( x, y, Trap() )


        # The master plane does not do any sliding on its own, but we need to set
        # its slide y to "max" for rendering purposes.
        # Having loaded the level structure, we can default the slide values...
        master_plane.slide_x = master_plane.get_width() * TILE_WIDTH
        master_plane.slide_y = master_plane.get_height() * TILE_HEIGHT


        # Return a handle to the master plane
        return master_plane


    # Old, unused
    def update_master_plane(self):
        pass


    def build_bounds_plane(self, perimeter_maps):

        log2("building bounds plane")

        # Establish a fresh bounds plane...
        bounds_plane = self.create_plane()

        # Pad by 2 tiles on each side (thus, +4 width, +4 height)
        bounds_plane.tiles = DataGrid( self.master_plane.tiles.get_width() + (2 * COLLISION_BOUNDARY_SIZE), self.master_plane.tiles.get_height() + (2 * COLLISION_BOUNDARY_SIZE) )

        """
        for y in range( 0, self.master_plane.tiles.get_height() ):

            temp_row = []

            for x in range( 0, self.master_plane.tiles.get_width() ):
                temp_row.append(0)

            bounds_plane.tiles.append(temp_row)
        """


        # Pad the bounds plane by 2 on each axis; we want a 1-tile frame
        #bounds_plane.pad(w = 2, h = 2)


        # Now define the boundaries
        for key in perimeter_maps:

            m = perimeter_maps[key]

            # If the perimeter map is to the active map's left, we'll define left border...
            if ( (m.x < self.x) and (m.width > 0) ):

                # Perimeter map's relative position
                (rel_x, rel_y) = (
                    m.x - self.x,
                    m.y - self.y
                )

                # Only flush-aligned maps merit consideration here...
                #if ( abs(rel_x) == m.width ):
                if ( (abs(rel_x) - m.width) in range(0, COLLISION_BOUNDARY_SIZE) ):

                    # Go down the perimeter map...
                    for y in range( 0, m.master_plane.tiles.get_height() ):

                        # Obey boundary size
                        for x in range( 0, COLLISION_BOUNDARY_SIZE ):

                            # Get the relative ty
                            rel_ty = y + rel_y

                            if ( rel_ty >= -1 and rel_ty < 1 + self.master_plane.tiles.get_height() ):

                                # Only set the bounds for blocking tiles
                                #if ( m.master_plane.get_tile_index_collision_type(m.master_plane.tiles[y][-1] in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY
                                bounds_plane.tiles.write(
                                    (COLLISION_BOUNDARY_SIZE - 1 - x),
                                    COLLISION_BOUNDARY_SIZE + rel_ty,
                                    m.master_plane.tiles.read(
                                        m.master_plane.tiles.get_width() - 1 - x,
                                        y
                                    )
                                )

            # Check the right border, alternatively
            elif ( (m.x > self.x) and (m.width > 0) ):

                (rel_x, rel_y) = (
                    m.x - self.x,
                    m.y - self.y
                )

                # It must be flush on the right edge of the current map...
                #if ( abs(rel_x) == self.width ):
                if ( (abs(rel_x) - self.width) in range(0, COLLISION_BOUNDARY_SIZE) ):

                    # Go down the side...
                    for y in range( 0, m.master_plane.tiles.get_height() ):

                        # Obey boundary size
                        for x in range( 0, COLLISION_BOUNDARY_SIZE ):

                            rel_ty = y + rel_y

                            if ( rel_ty >= -1 and rel_ty < 1 + self.master_plane.tiles.get_height() ):

                                bounds_plane.tiles.write(
                                    bounds_plane.tiles.get_width() - (COLLISION_BOUNDARY_SIZE - x),
                                    COLLISION_BOUNDARY_SIZE + rel_ty,
                                    m.master_plane.tiles.read(x, y)
                                )
                                #][-1] = m.master_plane.tiles[y][0]


            # If the perimeter map is to the active map's north, we'll define top border...
            if ( (m.y < self.y) and (m.height > 0) ):

                # Perimeter map's relative position
                (rel_x, rel_y) = (
                    m.x - self.x,
                    m.y - self.y
                )

                # Only flush-aligned maps merit consideration here...
                #if ( abs(rel_y) == m.height ):
                if ( (abs(rel_y) - m.height) in range(0, COLLISION_BOUNDARY_SIZE) ):

                    # Go along the perimeter map...
                    for x in range( 0, m.master_plane.tiles.get_width() ):

                        # Obey boundary size
                        for y in range( 0, COLLISION_BOUNDARY_SIZE ):

                            # Get the relative tx
                            rel_tx = x + rel_x

                            if ( rel_tx >= -1 and rel_tx < 1 + self.master_plane.tiles.get_width() ):

                                # Only set the bounds for blocking tiles
                                #if ( m.master_plane.get_tile_index_collision_type(m.master_plane.tiles[y][-1] in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY
                                #bounds_plane.tiles[0][1 + rel_tx] = m.master_plane.tiles[-1][x]
                                bounds_plane.tiles.write(
                                    COLLISION_BOUNDARY_SIZE + rel_tx,
                                    (COLLISION_BOUNDARY_SIZE - 1 - y),
                                    m.master_plane.tiles.read(
                                        x,
                                        m.master_plane.tiles.get_height() - 1 - y
                                    )
                                )

            # Check the bottom border, alternatively
            elif ( (m.y > self.y) and (m.height > 0) ):

                (rel_x, rel_y) = (
                    m.x - self.x,
                    m.y - self.y
                )

                # It must be flush on the bottom edge of the current map...
                #if ( abs(rel_y) == self.height ):
                if ( (abs(rel_y) - self.height) in range(0, COLLISION_BOUNDARY_SIZE) ):

                    # Go along the side...
                    for x in range( 0, m.master_plane.tiles.get_width() ):

                        # Obey boundary size
                        for y in range( 0, COLLISION_BOUNDARY_SIZE ):

                            rel_tx = x + rel_x

                            if ( rel_tx >= -1 and rel_tx < 1 + self.master_plane.tiles.get_width() ):

                                #bounds_plane.tiles[-1][1 + rel_tx] = m.master_plane.tiles[0][x]
                                bounds_plane.tiles.write(
                                    COLLISION_BOUNDARY_SIZE + rel_tx,
                                    bounds_plane.tiles.get_height() - (COLLISION_BOUNDARY_SIZE - y),
                                    m.master_plane.tiles.read(x, y)
                                )


        #log2( "width: %s, height: %s\n" % (len(bounds_plane.tiles[0]), len(bounds_plane.tiles)), "high-left tile: %s\nlow-right tile: %s" % (bounds_plane.tiles[0][0], bounds_plane.tiles[-1][-1]) )


        """
        logn( "plane debug", "BOUNDS PLANE:\n" )
        for y in range( 0, bounds_plane.tiles.get_height() ):
            s = ""
            for x in range( 0, bounds_plane.tiles.get_width() ):
                s += "%s\t" % bounds_plane.tiles.read(x, y)
            logn( "plane debug", s )
        logn( "plane debug", "\n\n" )
        logn( "plane debug", "MASTER PLANE:\n" )
        for y in range( 0, self.master_plane.tiles.get_height() ):
            s = ""
            for x in range( 0, self.master_plane.tiles.get_width() ):
                s += "%s\t" % self.master_plane.tiles.read(x, y)
            logn( "plane debug", s )
        logn( "plane debug", "\n\n" )
        """


        self.master_plane.bounding_plane = bounds_plane



    def get_plane_in_midshift(self):

        for plane in self.planes:

            if (plane.is_shifting):
                return plane

        return None

    def get_plane_by_name(self, name):

        for plane in self.planes:

            if (plane.name == name):
                return plane

        return None


    def remove_plane_from_master_plane(self, plane):

        # Only remove non-modal planes (modal planes, such as the mask layer, never merge in the first place)
        if ( (not plane.is_modal) ):

            # Offset for individual plane
            lx = plane.x + int(plane.shift_x / TILE_WIDTH)
            ly = plane.y + int(plane.shift_y / TILE_HEIGHT)

            for ty in range( ly, ly + plane.tiles.get_height() ):

                for tx in range( lx, lx + plane.tiles.get_width() ):

                    # Does the plane we're erasing have tile data at this location?
                    if ( plane.get_tile_backup(tx - lx, ty - ly) > 0 ):

                        # Erase tile on master plane
                        self.master_plane.set_tile(tx, ty, 0)
                        self.master_plane.set_tile_backup(tx, ty, 0)

                        if (1):
                            # Check other planes, maybe there's an overlap with tile data
                            for other in self.planes:

                                # Only other planes
                                if ( (other != plane) and (not other.is_modal) ):

                                    # Relative position
                                    lxOther = other.x + int(other.shift_x / TILE_WIDTH)
                                    lyOther = other.y + int(other.shift_y / TILE_HEIGHT)

                                    # Tile data?
                                    if ( other.get_tile_backup(tx - lxOther, ty - lyOther) > 0 ):

                                        # Fall back to the overlapping plane's tile data
                                        self.master_plane.tiles.write( tx, ty, other.get_tile_backup(tx - lxOther, ty - lyOther) )
                                        self.master_plane.tiles_backup.write( tx, ty, other.get_tile_backup(tx - lxOther, ty - lyOther) )


                            # If after checking all other planes we determine that no other plane has tile data
                            # for this location, we will cancel any trap timer on this tile.
                            if ( self.master_plane.get_tile(tx, ty) == 0 ):

                                # Cancel trap timer data by writing a fresh, default Trap object
                                self.master_plane.traps.write( tx, ty, Trap() )

                            # If we found a fallback tile, we want to briefly erase it, because we sort of
                            # "dug" it out of the way to fit the shifting platform in.  After the platform leaves, it can refill...
                            else:

                                # Ladders and stuff don't matter, they're never "in the way" of a moving platform.
                                if ( self.master_plane.check_collision(tx, ty) in (COLLISION_DIGGABLE,) ):

                                    # Don't want to obstruct the plane we're removing, which has priority for shifting.
                                    self.master_plane.dig_tile_at_tile_coords(tx, ty, scripted_dig = True)

                                # Erase any trap that existed at this point on the master plane, it's just a ladder or monkey bar or something...
                                else:

                                    self.master_plane.traps.write( tx, ty, Trap() )


            #for row in self.master_plane.tiles.data:
            #    print row
            #print 5/0


        # Update the master plane's gold cache...
        self.master_plane.build_gold_cache()

    def merge_plane_into_master_plane(self, plane):

        if (SHOW_HACKS):
            log( "Add in reset data for tiles_backup as well???  Maybe, maybe not.  It's a challenge..." )

        # Only merge active, non-modal planes
        if ( (plane.active) and (not plane.is_modal) ):

            # Offset information
            lx = plane.x + int(plane.shift_x / TILE_WIDTH)
            ly = plane.y + int(plane.shift_y / TILE_HEIGHT)

            for ty in range( ly, ly + plane.tiles.get_height() ):

                for tx in range( lx, lx + plane.tiles.get_width() ):

                    # I think we want tiles_backup here now...
                    if ( plane.get_tile_backup(tx - lx, ty - ly) > 0 ):

                        # Update master plane
                        self.master_plane.set_tile(tx, ty, plane.get_tile_backup(tx - lx, ty - ly))
                        self.master_plane.set_tile_backup(tx, ty, plane.get_tile_backup(tx - lx, ty - ly))


                        # If the plane we're merging in wasn't dug at the current tile location,
                        # then it supersedes any existing trap/tile on the master plane.
                        if ( plane.traps.read(tx - lx, ty - ly).get_timer() == 0 ):

                            # Write a fresh, default Trap object to the master plane, erasing any existing trap...
                            self.master_plane.traps.write( tx, ty, Trap() )

                        # Otherwise, let's steal the timer from the individual plane and place it on the master plane
                        else:

                            # Thanks.  This might lead to shared traps, if player digs tile on two overlapping planes.  Probably doesn't matter, they're the same trap anyway, right?
                            self.master_plane.traps.write( tx, ty, plane.traps.read(tx - lx, ty - ly) )


                        # Fetch Trap object at this tile location
                        trap = self.master_plane.traps.read(tx, ty, default_value = None)

                        # Validate
                        if (trap):

                            # Timer active?
                            if ( trap.get_timer() > 0 ):

                                # Set tile to empty, waiting to refill...
                                self.master_plane.tiles.write(tx, ty, 0)


        # Update the master plane's gold cache...
        self.master_plane.build_gold_cache()

    # Before a planar shift, the master plane will distribute its
    # trap data to all of the child planes.  It will then regather
    # the trap data at the planar shift's conclusion...
    def distribute_master_trap_data_to_shifting_plane(self, shifting_plane):

        # Distribute to static planes, becauase we're about to render each plane individually.
        for plane in self.planes:
            #plane = self.get_plane_in_midshift()

            #if (plane):
            if ( (not plane.is_shifting) and (not plane.is_sliding) and (not plane.is_modal) ):

                self.copy_master_trap_data_to_plane(plane)


        self.copy_master_trap_data_to_plane(shifting_plane)


    def copy_master_trap_data_to_plane(self, plane):

        (tx, ty) = (
            plane.x + int(plane.shift_x / TILE_WIDTH),
            plane.y + int(plane.shift_y / TILE_HEIGHT)
        )

        for y in range(ty, ty + plane.get_height()):

            for x in range(tx, tx + plane.get_width()):

                #if ( plane.get_tile_index_collision_type(plane.tiles_backup[y - ty][x - tx]) == COLLISION_DIGGABLE ):
                if ( plane.tiles_backup.read(x - tx, y - ty) > 0 ): # Always do this, if the tile's already dug, it's dug!  (?!)

                    # Get the Trap object at the current tile location
                    trap = self.master_plane.traps.read(x, y, default_value = None)

                    # Copy (reuse) the Trap object to the plane...
                    plane.traps.write(
                        x - tx,
                        y - ty,
                        trap
                    )


                    # Validate trap object
                    if (trap):

                        # Immediately reset the master plane's trap occupant data if necessary;
                        # a trapped enemy can belong to only one plane at any given time.
                        if ( trap.get_occupants() > 0 ):
                            trap.set_occupants(0)


                        # Set tile data on the individual plane to 0 if there's a trap there...
                        if ( trap.get_timer() > 0):
                            plane.tiles.write(x - tx, y - ty, 0)

                        # (?)
                        else:

                            plane.tiles.write(
                                x - tx,
                                y - ty,
                                plane.get_tile_backup(x - tx, y - ty)
                            )


    def recollect_master_trap_data_from_shifting_plane(self, plane):

        return

        #for plane in self.planes:
        if (True):
            #plane = self.get_plane_in_midshift()

            #if (plane):

            (tx, ty) = (
                plane.x + int(plane.shift_x / TILE_WIDTH),
                plane.y + int(plane.shift_y / TILE_HEIGHT)
            )

            for y in range(ty, ty + plane.get_height()):

                for x in range(tx, tx + plane.get_width()):

                    # Ignore planes in motion, and ignore modal planes
                    if ( (not plane.is_shifting) and (not plane.is_sliding) and (not plane.is_modal) ):

                        # Does the plane have tile data at this location?
                        if ( plane.get_tile_backup(x - tx, y - ty) > 0 ):

                            # Get Trap object at the current location on the individual plane
                            trap = plane.traps.read(x - tx, y - ty, default_value = None)

                            # Validate Trap object
                            if (trap):

                                # Share back with the master plane, though I think it's the same object that's already there...
                                self.master_plane.traps.write(x, y, trap)

                                # If the trap is still active, then we'll erase the tile on the master plane until it refills...
                                if ( trap.get_timer() > 0 ):

                                    # Erase
                                    self.master_plane.tiles.write(x, y, 0)


    # Handle level editor input for this map
    def handle_editor_input(self, editor_input, control_center):

        # Fetch the editor controller
        editor_controller = control_center.get_editor_controller()


        # Paint a tile?
        if ( (editor_input["paint-tile"] == True) and (editor_input["can-paint"] == True) ):

            # Begin by calculating the active tile.  We base this on the mouse cursor's position
            # relative to the origin of the current planet. (?)
            #(mx, my) = (editor_input["mouse-rel-x"], editor_input["mouse-rel-y"])

            # Tile coordinates of target
            (tx, ty) = (
                editor_controller.mouse.tx,
                editor_controller.mouse.ty
            )


            # Use the current plane
            plane = self.planes[ self.active_plane_z_index ]

            # Sanity
            if (tx >= plane.x and ty >= plane.y):

                # Paint tile
                plane.set_tile( (tx - plane.x), (ty - plane.y), editor_controller.tile )


    def create_particle_effect(self, x, y, tile_index):

        for j in range(0, 3):
            for i in range(0, 3):

                self.particles.append( Particle(x, y, tile_index, i, j) )


    def create_gold_spinner(self, x, y):

        self.gold_spinners.append( GoldSpinner(x, y, 0, 0) )

    def dig_tile_at_tile_coords(self, tx, ty, purge = False, scripted_dig = False, duration_multiplier = 1, force_dig = False):

        result = self.master_plane.dig_tile_at_tile_coords(tx, ty, purge, scripted_dig, duration_multiplier, force_dig)

        # If the dig succeeds, then we will create some particles...
        if (result == DIG_RESULT_SUCCESS):

            # Calculate top left position
            (x, y) = (self.master_plane.x + (tx * TILE_WIDTH), self.master_plane.y + (ty * TILE_HEIGHT))

            # Create particle effect
            self.create_particle_effect(x, y, self.master_plane.tiles_backup.read(tx, ty))

        return result


    def place_magic_wall_at_tile_coords(self, tx, ty, direction, lifespan, has_spikes):

        # Can we place a magic wall at this location?  It must have solid ground beneath it, and it must occupy an empty space...
        if (self.master_plane.check_collision(tx, ty + 1, strictly_within_level = True) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE) and
            self.master_plane.check_collision(tx, ty, strictly_within_level = True) in (COLLISION_NONE,)):

            self.magic_wall = MagicWall(tx, ty, direction, lifespan, has_spikes, covered_tile_index = self.master_plane.get_tile(tx, ty))

            return True

        else:

            return False


    def destroy_magic_wall(self):

        # If we have a magic wall...
        if (self.magic_wall):

            # ... destroy it.
            self.magic_wall.destroy_on_map(self)

            # Lose the reference
            self.magic_wall = None


    def trap_exists_at_tile_coords(self, tx, ty, exception):

        if (self.master_plane.trap_exists_at_tile_coords(tx, ty, exception)):
            return True

        return False


    def is_dialogue_finished(self):

        return (self.dialogue_panel == None)


    def handle_player_arrival(self, control_center, universe):

        # Why did I have this in here?  It looks unnecessary...
        """
        # Reset the wave tracker whenever a player re-visits a map
        #self.reset_wave_tracker()
        """


        # Check to see if the map has an on-arrival script
        if ( self.does_script_exist("on-arrival") ):

            # The on-arrival script is typically just a bunch of flag settings and such,
            # so we make sure to run through everything we can immediately...
            self.run_script("on-arrival", control_center, universe, execute_all = True)


        #log2( "Deactivated first movement AI delay for debugging..." )
        #return

        # Player inventory can affect first movement delay
        modifier = (
            1.0 +
            sum( o.attributes["enemy-first-movement-wait-bonus"] for o in universe.get_equipped_items() )
        )

        # Make every enemy delay for a short while so the player
        # can see what's going on...
        first_movement_delay = int(modifier * AI_ENEMY_INITIAL_DELAY)# + sum(o.attributes["enemy-first-movement-wait-bonus"] for o in universe.equipped_inventory)


        # Disable enemy first movement delay within GIF previews
        # (Hard-coded hack)
        if (
            int( universe.get_session_variable("core.is-gif").get_value() ) != 1 and
            not ("--recording" in sys.argv)
        ):

            # Each enemy will delay briefly
            for e in self.master_plane.entities[GENUS_ENEMY]:

                # Delay
                e.hesitate(first_movement_delay)


    def handle_player_departure(self, control_center, universe):

        # Remove any non-detonated remote bombs
        for bomb in  self.get_entities_by_type(GENUS_BOMB):

            # Remote bomb?
            if (bomb.is_remote()):

                # Flag it to disappear...
                bomb.remove_silently()

        # Reset the concurrent remote bombs flag for the player...
        #universe.set_session_variable("core.skills.remote-bomb:bombs-remaining", "0")


        # Check to see if the map has an on-departure script
        if ( self.does_script_exist("on-departure") ):

            # The on-departure script is typically just a bunch of flag settings and such,
            # so we make sure to run through everything we can immediately...
            self.run_script("on-departure", control_center, universe, execute_all = True)


    #def process(self, user_input, widget_dispatcher, network_controller, universe, session, quests):
    def process(self, control_center, universe):

        if ( not universe.is_locked() ):

            if (self.hack_panel):

                if (not self.hack_panel.is_fading()):
                    self.hack_panel.process(user_input, session)

                else:
                    self.hack_panel.process([], {})


                if (self.hack_panel.is_gone()):
                    self.hack_panel = None


                # Keep the event controller going through the login attempt...
                result = self.event_controller.process(network_controller, universe, self, session, quests)

                while (result == True):
                    result = self.event_controller.process(network_controller, universe, self, session, quests)

            elif (self.dialogue_panel):

                if (not self.dialogue_panel.is_fading()):

                    result = self.dialogue_panel.process(user_input, universe, session)

                    # If we got a response from the current line, then we'll
                    # soon hop to another dialogue line...
                    if ( (result != None) and (result != "") ):

                        self.queued_branch = result

                else:

                    self.dialogue_panel.process([], universe, session)


                if (self.dialogue_panel.is_gone()):


                    # Did the line have any post-script data?  We'll try to handle it immediately...
                    if (self.dialogue_panel.ref_line.post_script):

                        # I want to handle these events immediately.  You can't use blocking events (successfully) in a pre-script...
                        #controller = EventController()

                        self.event_controller.load_events_from_xml_packet(self.dialogue_panel.ref_line.post_script)

                        #print self.dialogue_panel.ref_line.post_script.compile_xml_string()
                        #print 5/0


                        # Run for as long as possible.  You can only inject simple single-use events...
                        #result = controller.process(self, session, quests)

                        #while (result == True):
                        #    result = controller.process(self, session, quests)



                    # Should we continue the conversation?
                    if (self.queued_branch):

                        entity = self.dialogue_panel.narrator
                        conversation = self.dialogue_panel.conversation

                        log( "Branch keys for '%s':" % conversation )
                        for key in entity.conversations[conversation].branches:
                            log( "\t%s" % key )

                        line = entity.conversations[conversation].branches[ self.queued_branch ].get_next_line()

                        if (line):

                            if (line.script):

                                if (line.script in self.scripts):

                                    # Append events...
                                    self.event_controller.load_packets_from_xml_node( self.scripts[line.script] )


                                    # Run for as long as possible.  You can only inject simple single-use events...
                                    #result = controller.process(self, session, quests)

                                    #while (result == True):
                                    #    result = controller.process(self, session, quests)

                            self.create_dialogue_panel(line, universe, session, quests, conversation, entity, self.dialogue_panel.event_type)

                        self.queued_branch = None

                    # Redirect to another branch following the line?
                    elif (self.dialogue_panel.redirect):

                        entity = self.dialogue_panel.narrator
                        conversation = self.dialogue_panel.conversation

                        line = entity.conversations[conversation].branches[ self.dialogue_panel.redirect ].get_next_line()

                        if (line):

                            if (line.pre_inject_script_name):

                                script = line.pre_inject_script_name

                                if (script in self.scripts):

                                    # Immediately run these scripts in a disposable event controller
                                    controller = EventController()

                                    controller.load_packets_from_xml_node( self.scripts[script] )


                                    # Run for as long as possible.  You can only inject simple single-use events...
                                    result = controller.process(universe, self, session, quests)

                                    while (result == True):
                                        result = controller.process(universe, self, session, quests)

                            self.create_dialogue_panel(line, universe, session, quests, conversation, entity, shop = (self.dialogue_panel.species == "shop"))

                    # Nope; we're done talking for now...
                    else:

                        self.dialogue_panel = None


                result = self.event_controller.process(network_controller, universe, self, session, quests)

                while (result == True):
                    result = self.event_controller.process(network_controller, universe, self, session, quests)


            else:

                # If the map isn't active, we won't be processing any object...
                if ( not (self.get_status() == STATUS_ACTIVE) ):

                    # if we're in a cutscene, though, we'll handle any scripting requests...
                    if ( self.get_status() == STATUS_CUTSCENE ):

                        # Check for map events
                        #result = self.event_controller.process(network_controller, universe, self, session, quests)
                        result = self.event_controller.process(control_center, universe)

                        while (result == True):

                            # Continue checking for map events
                            #result = self.event_controller.process(network_controller, universe, self, session, quests)
                            result = self.event_controller.process(control_center, universe)

                    return

                else:

                    # Increment completion time
                    self.completion_time += 1


                    # First activated trigger that the player is touching will get priority.
                    # By default, none is masked...
                    masked = False

                    # Process triggers first...
                    for t in self.triggers:

                        # Check whether or not the current trigger has detected a player intersection, claiming dibs basically...
                        masked |= t.process(control_center, universe, is_editor = False, masked = masked)#widget_dispatcher, network_controller, universe, self, session, user_input, is_editor = False) # We only process() in game mode
                        #pass


                    # Increment fall region timer
                    self.fall_region_timer += 1

                    # Reset to 0 as necessary
                    if (self.fall_region_timer > FALL_REGION_TIMER_MAX):

                        # Reset
                        self.fall_region_timer = 0


                    # Do we have a magic wall to process?
                    if (self.magic_wall):

                        # When the magic wall is "ready," it will use the "self" (map) to install itself on the collision grid...
                        self.magic_wall.process(control_center, universe)

                        # If the magic wall has expired, we should discard it...
                        if (self.magic_wall.state == STATUS_INACTIVE):

                            self.magic_wall = None


                    #self.master_plane.process(user_input, network_controller, universe, self, session)
                    self.master_plane.process(control_center, universe)


                    """
                    # Check for map events
                    #result = self.event_controller.process(network_controller, universe, self, session, quests)
                    result = self.event_controller.process(control_center, universe)

                    while (result == True):

                        # See if we shoudl continue looping
                        #result = self.event_controller.process(network_controller, universe, self, session, quests)
                        result = self.event_controller.process(control_center, universe)
                    """
                    self.event_controller.loop(control_center, universe)


                    for particle in self.particles:
                        particle.process(None)

                    for colorcle in self.colorcles:
                        colorcle.process(None)

                    for numbercle in self.numbercles:
                        numbercle.process(None)

                    for gold_spinner in self.gold_spinners:
                        gold_spinner.process(None)


    # Processing that happens during a cutscene
    def process_cutscene(self, control_center, universe):

        # if we're in a cutscene, though, we'll handle any scripting requests...
        if ( 1 or ( self.get_status() == STATUS_CUTSCENE ) ):

            # Check for map events
            #result = self.event_controller.process(network_controller, universe, self, session, quests)
            result = self.event_controller.process(control_center, universe)

            while (result == True):

                # Continue checking for map events
                result = self.event_controller.process(control_center, universe)


    def process_drama(self, control_center, universe):

        for genus in self.master_plane.entities:

            for entity in self.master_plane.entities[genus]:

                entity.process_drama(control_center, universe)

    def process_sound(self):

        # Which sounds will we want to play?
        keys = []

        for genus in (GENUS_PLAYER, GENUS_BOMB, GENUS_HOLOGRAM):

            for e in self.master_plane.entities[genus]:

                while ( len(e.sfx_queue) > 0 ):

                    keys.append( e.sfx_queue.pop(0) )
                    #print "play ", sfx_key

                    #self.sound_effects[sfx_key].play()

        return keys

    def post_process(self, control_center, universe):#network_controller, universe, session):

        if ( not universe.is_locked() ):

            #for plane in self.planes:
            #    plane.post_process(self)

            self.master_plane.post_process(control_center, universe)#network_controller, universe, self, session)

            # Remove lost particles
            i = 0

            while (i < len(self.particles)):

                if (self.particles[i].state == False):
                    self.particles.pop(i)

                else:
                    i += 1


            # Remove lost colorcles
            i = 0

            while (i < len(self.colorcles)):

                if (self.colorcles[i].state == False):
                    self.colorcles.pop(i)

                else:
                    i += 1


            # Remove lost numbercles
            i = 0

            while (i < len(self.numbercles)):

                if (self.numbercles[i].state == False):
                    self.numbercles.pop(i)

                else:
                    i += 1


            # Remove lost gold spinners
            i = 0

            while (i < len(self.gold_spinners)):

                if (self.gold_spinners[i].state == False):
                    self.gold_spinners.pop(i)

                else:
                    i += 1


            # Remove corpsed GHOST enemies
            for genus in (GENUS_ENEMY,):

                i = 0

                while (i < len(self.master_plane.entities[genus])):

                    if ( (self.master_plane.entities[genus][i].is_ghost) and (self.master_plane.entities[genus][i].corpsed == True) and (not self.master_plane.entities[genus][i].twitching()) ):

                        self.master_plane.entities[genus].pop(i)

                    else:

                        i += 1


            # Remove corpsed bombs, holograms permanently
            for genus in (GENUS_BOMB, GENUS_HOLOGRAM):

                i = 0

                while (i < len(self.master_plane.entities[genus])):

                    if ( self.master_plane.entities[genus][i].corpsed == True and (not self.master_plane.entities[genus][i].twitching()) ):

                        log( "let's remove '%s'" % self.master_plane.entities[genus][i].name )
                        self.master_plane.entities[genus].pop(i)

                    else:
                        i += 1


    # Check to see if this map has existing replay data
    def has_replay_data(self):

        # Simple check
        return ( len(self.replay_data) > 0 )


    # Some GIFs provide predefined replay data to a Map object to create an animation...
    def process_replay_data(self, control_center, universe):

        # If we have replay data remaining, let's send it to the active map
        if ( self.replay_cursor < len(self.replay_data) ):

            # Get serialized data
            data = self.replay_data[self.replay_cursor].strip()

            # Create a list to hold emulated user input for the current frame
            user_input = []

            # Loop data
            if ( len(data) > 0 ):

                # We saved replay data as a csv string
                for s in data.split(","):

                    # Add to user input
                    user_input.append(
                        int(s)
                    )


            # Get the local player object, if/a
            player = self.get_entity_by_name("player1")

            # Validate player object
            if (player):

                # Send input data to player1 entity using the given universe
                player.handle_user_input( user_input, control_center, universe )


            # Advance the replay cursor
            self.replay_cursor += 1

        # For now, I'm going to manually activate the "reload map" flag if we reach the end of a
        # given set of replay commands.
        elif ( self.replay_cursor > 0 ):

            # We'll start from the beginning...
            self.requires_reload = True


    # Sometimes a map the player just left has some leftover particles...
    def process_particles_only(self):

        for particle in self.particles:
            particle.process(None)

        # Check to remove them as needed...
        i = 0

        while (i < len(self.particles)):
            if (self.particles[i].state == False):
                self.particles.pop(i)

            else:
                i += 1


        for colorcle in self.colorcles:
            colorcle.process(None)

        # Check to remove them as needed...
        i = 0

        while (i < len(self.colorcles)):
            if (self.colorcles[i].state == False):
                self.colorcles.pop(i)

            else:
                i += 1


        for numbercle in self.numbercles:
            numbercle.process(None)

        # Check to remove them as needed...
        i = 0

        while (i < len(self.numbercles)):
            if (self.numbercles[i].state == False):
                self.numbercles.pop(i)

            else:
                i += 1


        for gold_spinner in self.gold_spinners:
            gold_spinner.process(None)

        # Check to remove them as needed...
        i = 0

        while (i < len(self.gold_spinners)):
            if (self.gold_spinners[i].state == False):
                self.gold_spinners.pop(i)

            else:
                i += 1


    # Render the map at some absolute location (without any regard for the map's real location within the universe)
    # I primarily use this for rendering movies, GIFs maybe...
    def draw_in_place(self, x, y, tilesheet_sprite, additional_sprites, game_mode, gl_color = None, text_renderer = None, window_controller = None):

        self.draw( x - (self.x * TILE_WIDTH), y - (self.y * TILE_HEIGHT), tilesheet_sprite, additional_sprites, game_mode, gl_color, text_renderer, window_controller)


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, game_mode, gl_color = None, text_renderer = None, control_center = None, max_x = SCREEN_WIDTH, max_y = SCREEN_HEIGHT, scale = 1):

        # Fetch window controller
        window_controller = control_center.get_window_controller()

        """
        # Render position
        (rx, ry) = (
            sx + (self.x * TILE_WIDTH),
            sy + (self.y * TILE_HEIGHT)
        )

        # Default scale (100%)
        #scale = 1.0


        # Background layer maps scale (down)
        if (scale != 1):#self.layer == LAYER_BACKGROUND):

            # Lookup scale
            #scale = BACKGROUND_MAP_SCALE

            # Adjust render point accordingly
            (rx, ry) = (
                sx + int( scale * (self.x * TILE_WIDTH) ),
                sy + int( scale * (self.y * TILE_HEIGHT) )
            )

        """

        (rx, ry) = (sx, sy)

        if (game_mode == MODE_GAME):

            # Render individual planes during cutscenes...
            if ( self.get_status() == STATUS_CUTSCENE ):

                for plane in self.planes:

                    if (plane.active):

                        plane.render(rx, ry, tilesheet_sprite, additional_sprites, gl_color = gl_color, is_editor = (game_mode == MODE_EDITOR), window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)

                # Only the master plane holds entities and stuff, though!
                self.master_plane.render(rx, ry, tilesheet_sprite, additional_sprites, render_sprites_not_tiles = True, gl_color = gl_color, is_editor = (game_mode == MODE_EDITOR), window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)

            else:

                self.master_plane.render(rx, ry, tilesheet_sprite, additional_sprites, gl_color = gl_color, is_editor = (game_mode == MODE_EDITOR), window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)

                # Render any modal, mask planes...
                for plane in self.planes:

                    if (plane.active and plane.is_modal):

                        plane.render(rx, ry, tilesheet_sprite, additional_sprites, gl_color = gl_color, is_editor = (game_mode == MODE_EDITOR), window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)

                # Render sprites on top of mask plane(s)
                self.master_plane.render(rx, ry, tilesheet_sprite, additional_sprites, render_sprites_not_tiles = True, gl_color = gl_color, is_editor = False, window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)


                # Do we have a magic wall to render?
                if (self.magic_wall):
                    self.magic_wall.draw(rx, ry, tilesheet_sprite, None)


            # Draw any trigger... essentially just draws the prompt when necessary
            for t in self.triggers:

                # Brutal hack!  gl_color[0] < 1 indicates we're rendering this map dim,
                # in which case we fake the is_Cutscene parameter to be True, and thus prevent rendering of trigger tooltips for offscreen maps!
                t.draw(rx, ry, additional_sprites, text_renderer, show_name = False, show_frame = False, is_editor = False, is_cutscene = ( (gl_color[0] < 1) or (self.get_status() == STATUS_CUTSCENE) ), window_controller = window_controller)


            # If this is the active map, we should render any fall region lines.
            if (gl_color[0] == 1):

                # Calculate which side of the fall region line (left/right) we want to render.
                lx = 0

                # Scope
                lcolor = None


                # If we're beyond halftime, we'll render the right half...
                if ( self.fall_region_timer >= int(FALL_REGION_TIMER_MAX / 2) ):

                    # Advance to the right half
                    lx += int(TILE_WIDTH / 2)


                    # How far through the timer's max duration have we ticked?
                    # Subtract 1.0 to account for first half (i.e. left side).
                    interval = (self.fall_region_timer / float(FALL_REGION_TIMER_MAX / 2)) - 1.0

                    # Are we fading in?
                    if (interval <= 0.5):

                        # Set color
                        lcolor = (195, 175, 25, min( interval * 2, 1.0 ))

                    # No, we're fading out.
                    else:

                        # Set color using complement
                        lcolor = (195, 175, 25, min( 2.0 - (interval * 2), 1.0 ))

                # If we're not beyond halftime, we're rendering the left half...
                else:

                    # How far through the timer's max duration have we ticked?
                    interval = (self.fall_region_timer / float(FALL_REGION_TIMER_MAX / 2))

                    # Are we fading in?
                    if (interval <= 0.5):

                        # Set color
                        lcolor = (195, 175, 25, min( interval * 2, 1.0 ) / 2)

                    # No, we're fading out.
                    else:

                        # Set color using complement
                        lcolor = (195, 175, 25, min( 2.0 - (interval * 2), 1.0 ) / 2)


                # Loop fall regions
                for r in self.get_fall_regions():

                    # Convert from tile coordinates to absolute coordinates
                    (x, y, w, h) = (
                        rx + (r[0] * TILE_WIDTH),
                        ry + self.get_height_in_pixels() + TILE_HEIGHT,
                        r[1] * TILE_WIDTH,
                        1 # Hard-coded
                    )

                    # Render a dashed line
                    for i in range(0, r[1]):

                        # Render debug rect
                        window_controller.get_geometry_controller().draw_rect(
                            x + lx + (i * TILE_WIDTH),
                            y,
                            int(TILE_WIDTH / 2),
                            h,
                            lcolor
                        )


            # Render particles
            for particle in self.particles:
                particle.render(rx, ry, tilesheet_sprite, window_controller)

            # Render colorcles
            for colorcle in self.colorcles:
                colorcle.render(rx, ry, window_controller)

            # Render numbercles
            for numbercle in self.numbercles:
                numbercle.render(rx, ry, additional_sprites["numbercles"], window_controller)

            # Render gold spinner
            for gold_spinner in self.gold_spinners:
                gold_spinner.render(rx, ry, additional_sprites[GENUS_GOLD], window_controller)


            # I'm not currently using the map status message.  I was going to use it to show
            # quest prompts, but right now I've decided to skip the idea.
            """
            # Does the map currently have a status message worth rendering?
            if (self.status_message != ""):

                # Determin the message's width.
                w = text_renderer.size(self.status_message)

                # Padding
                (padding_x, padding_y) = (24, 6)

                # We'll center it at the bottom of the screen
                (rx, ry) = (
                    int(SCREEN_WIDTH / 2) - int( (w + (2 * padding_x)) /  2),
                    SCREEN_HEIGHT - 12 - text_renderer.font_height - (2 * padding_y)
                )

                # Render a background...
                window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                    rx,
                    ry,
                    w + (2 * padding_x),
                    text_renderer.font_height + (2 * padding_y),
                    background1 = (50, 50, 50, 0.5),
                    background2 = (20, 20, 20, 0.5),
                    border = (175, 175, 175, 0.8),
                    border_size = 2,
                    shadow = (125, 125, 125, 0.7),
                    shadow_size = 1,
                    gradient_direction = DIR_RIGHT
                )

                # Lastly, render the message itself...
                text_renderer.render(self.status_message, rx + padding_x, ry + padding_y, (225, 225, 225))
            """


            #if (gl_color[0] == 1):
            #    (lx, ly) = (rx - 24, ry - 24)
            #    plane = self.master_plane.bounding_plane
            #    if (plane):
            #        for y in range( 0, len(plane.tiles) ):
            #            for x in range( 0, len(plane.tiles[y]) ):
            #                if (plane.tiles[y][x] > 0):
            #                    text_renderer.render( "%d" % plane.tiles[y][x], lx + x * 24, ly + y * 24, (225, 225, 225, 0.7) )


        # In editor mode, we'll render each of the planes individually
        elif (game_mode == MODE_EDITOR):

            # Fetch editor controller
            editor_controller = control_center.get_editor_controller()

            # Render each plane independently; account for potential unsaved z-index changes
            for z in range(0, len(self.planes)):

                for plane in self.planes:

                    if (plane.z_index == z):

                        # Active plane?  Without previous gl_color imposition?
                        if (z == self.active_plane_z_index):

                            gl_color = coalesce(gl_color, (1, 1, 1, 1))

                            plane.render(rx, ry, tilesheet_sprite, additional_sprites, gl_color = gl_color, window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)

                        # No; display it kind of dimmed...
                        else:
                            plane.render(rx, ry, tilesheet_sprite, additional_sprites, gl_color = (0.5, 0.5, 0.5, gl_color[3]), window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)


            # Entities always belong to the master plane, even in the editor
            self.master_plane.render(rx, ry, tilesheet_sprite, additional_sprites, render_sprites_not_tiles = True, is_editor = True, window_controller = window_controller, max_x = max_x, max_y = max_y, scale = scale)


            # Frame each plane (or the active plane)
            for plane in self.planes:

                #if (plane.z_index == 
                if (plane.z_index == self.active_plane_z_index):

                    # Highlight as active
                    window_controller.get_geometry_controller().draw_rect_frame(
                        sx + int(scale * plane.x * TILE_WIDTH),
                        sy + int(scale * plane.y * TILE_HEIGHT),
                        int(scale * plane.get_width() * TILE_WIDTH),
                        int(scale * plane.get_height() * TILE_HEIGHT),
                        (37, 105, 255),
                        1
                    )

                else:

                    # Render dim border to signify it's its own plane, but it shouldn't stand out in any way
                    window_controller.get_geometry_controller().draw_rect_frame(
                        sx + int(scale * plane.x * TILE_WIDTH),
                        sy + int(scale * plane.y * TILE_HEIGHT),
                        int(scale * plane.get_width() * TILE_WIDTH),
                        int(scale * plane.get_height() * TILE_HEIGHT),
                        (75, 75, 75),
                        1
                    )


                # Check flag to see if the plane's dimensions have changed
                if (plane.updated_dimensions):

                    # Disable flag
                    plane.updated_dimensions = False

                    # Update this map's dimensions
                    self.update_dimensions()


            # Draw any trigger...
            for t in self.triggers:

                # Render trigger (bounding area and name, possibly)
                t.draw(rx, ry, additional_sprites, text_renderer, show_name = editor_controller.show_trigger_names, show_frame = editor_controller.show_trigger_frames, is_editor = True, window_controller = window_controller, scale = scale)


            # I don't expect to create particles during editor mode, but just in case...
            for particle in self.particles:

                # Render particle
                particle.render(rx, ry, tilesheet_sprite, window_controller)



            text_renderer.render_with_wrap(self.name, rx + 5, ry + 5, (225, 225, 25))


            # **Is this obsolete?  I don't know.  I think I calculate this at runtime in game mode only.  I'll leave it here for now...
            #if (self.master_plane.bounding_plane):
            #    log( "**Rendering bounding plane" )
            #    self.master_plane.bounding_plane.render(rx - TILE_WIDTH, ry - TILE_HEIGHT, tilesheet_sprite, additional_sprites, window_controller = window_controller)


        # Render hack panel?
        #if (self.hack_panel):

        #    self.hack_panel.render(text_renderer)

        # No?  Maybe a dialogue panel?
        #elif (self.dialogue_panel):

        #    self.dialogue_panel.render(text_renderer, additional_sprites, window_controller)

    def draw_overlays(self, additional_sprites, text_renderer = None, window_controller = None):

        # Render hack panel?
        if (self.hack_panel):

            self.hack_panel.render(text_renderer)

        # No?  Maybe a dialogue panel?
        elif (self.dialogue_panel):

            self.dialogue_panel.render(text_renderer, additional_sprites, window_controller)


    # I think this is unused, from back in the planetary, ring-based level days...
    """
    def set_tile(self, index, value):

        if ( index < self.tiles.get_height() ):

            self.tiles[index] = int(value)
    """


class Plane:

    def __init__(self, node = None, z_index = 0, visible = True):

        # I'm not sure "Untitled Plane" was the best choice for a default name, but that's what we're using now.
        self.name = "Untitled Plane"


        # The bounds plane, as an example, is never rendered.
        self.visible = visible

        # Default to active.  We can deactivate planes via script to make them disappear from the level.
        self.active = True


        # A plane will need (and eventually receive) a flat list
        # containing all collision values for the active tilesheet.
        self.collision_values_by_tile_index = [] # Default to no data


        # Grid coordinates (multiply by tile width/height for absolute pixel values)
        self.x = 0
        self.y = 0


        # On the rarest of occasions, we might set a plane to ignore map memory data
        self.ignore_previous_state = False


        # We can apply miscellaneous params to planes.  We typically use this feature
        # for tracking during scripting events (i.e. state variables).
        self.params = {}


        # Lock counter for this plane.
        self.lock_count = 0


        # Modal plane?  (mask layer)
        self.is_modal = False


        # Alpha control
        self.alpha_controller = IntervalController(
            interval = 1.0,
            target = 1.0,
            speed_in = 0.015,
            speed_out = 0.015
        )


        # Modified?  Dimensions changed?
        self.modified = False
        self.updated_dimensions = False

        # Z-index (used for level editor rendering order)
        self.z_index = z_index


        # Planar shift flag
        self.is_shifting = False

        # Planar shift offsets
        self.dx = 0
        self.dy = 0


        # Remember shift values (absolute pixel values)
        self.shift_x = 0
        self.shift_y = 0

        # Remember which entities were still affected at the end of the shift...
        self.shift_stowaways = []


        # Remember slide values... in load(), we'll default these to the plane's initial width/height...
        self.slide_x = 0
        self.slide_y = 0

        # We don't want to bother with the scissor test if we're not currently sliding...
        self.is_sliding = False




        # Track the structure of the plane
        self.tiles = DataGrid(0, 0)

        # We'll keep a copy for when we're filling holes back into existence
        self.tiles_backup = DataGrid(0, 0)


        # For each tile location, I'll track various trap data, such as dig state,
        # time left until refill, whether an enemy has fallen in already, etc.
        # With random fill patterns, we prevent awkward synchronicity effects when blocks refill...
        self.traps = DataGrid(0, 0)


        # Gold cache; which tiles have gold?  (Store the gold entity's name in the grid.)
        self.gold_cache = []


        # A plane might track a matrix delay for the matrix skill
        self.matrix_remaining = 0

        self.matrix_step = 0            # Only at step 0 will we process enemy logic
        self.matrix_step_max = 0        # How many steps does the matrix effect have?

        # Fright works in a similar way
        self.fright_remaining = 0





        # Master planes will track a bounding plane so that the player cannot enter
        # another map in violation of the perimeter map's collision detection...
        self.bounding_plane = None

        self.entities = {
            GENUS_PLAYER: [],
            GENUS_ENEMY: [],
            GENUS_NPC: [],
            GENUS_RESPAWN_PLAYER1: [],
            GENUS_RESPAWN_PLAYER2: [],
            GENUS_RESPAWN_PLAYER: [],
            GENUS_RESPAWN_ENEMY: [],
            GENUS_GOLD: [],
            GENUS_LEVER: [],
            GENUS_BOMB: [],
            GENUS_HOLOGRAM: []
        }

        if (node):
            self.load(node)


    def load(self, node):

        # Read position data
        self.x = int( node.get_attribute("x") )
        self.y = int( node.get_attribute("y") )


        # Check for ignore state flag
        if ( node.has_attribute("ignore-previous-state") ):
            self.ignore_previous_state = ( int( node.get_attribute("ignore-previous-state") ) == 1 )


        # Check for a given plane name
        if ( node.has_attribute("name") ):
            self.name = node.get_attribute("name")

        # Check for modal status (used for mask layer type planes, such as the mask layer and moving chains)
        if ( node.has_attribute("modal") ):
            self.is_modal = ( int( node.get_attribute("modal") ) == 1 )


        # Get the level structure
        ref = node.find_node_by_tag("structure")

        # Validate
        if (ref):

            # Load plane structure data
            self.load_structure(ref)


        # Having loaded the level structure, we can default the slide values...
        self.slide_x = self.get_width() * TILE_WIDTH
        self.slide_y = self.get_height() * TILE_HEIGHT


    def compile_xml_string(self, prefix = ""):

        # Save the plane
        xml = "%s<plane name = '%s' x = '%d' y = '%d' modal = '%d'>\n%s\t<structure>\n" % (prefix, self.name, self.x, self.y, self.is_modal, prefix)

        for y in range( 0, self.tiles.get_height() ):

            xml += "%s\t\t" % prefix
            for x in range( 0, self.tiles.get_width() ):

                xml += "%d " % self.tiles.read(x, y)

            xml += "\n"

        xml += "%s\t</structure>\n" % prefix

        xml += "%s</plane>\n" % prefix

        return xml


    def load_structure(self, node):

        # Reset tile data, backup tile data, and trap data
        self.tiles.clear()
        self.tiles_backup.clear()
        self.traps.clear()

        # Validate that we have data to load
        if ( node.innerText.strip() != "" ):

            # The innerText holds the tile sequence...
            data = node.innerText.strip()

            # Get rows
            rows = data.split("\n")

            # Loop rows
            for y in range( 0, len(rows) ):

                # Get columns
                cols = rows[y].strip().split(" ")

                # Loop columns
                for x in range( 0, len(cols) ):

                    # Convenience
                    tile = cols[x]

                    # Save tile data as current and "backup"
                    self.tiles.write(x, y, int(tile))
                    self.tiles_backup.write(x, y, int(tile))

                    # Add a new trap data object for this tile (everything at default, i.e. inactive)
                    self.traps.write(
                        x,
                        y,
                        Trap()
                    )

        #self.traps.debug = True


    # Save plane state
    def save_state(self):

        # Create node
        node = XMLNode("plane")

        # Set properties, unless this is the "Untitled Plane" I use for the base of each level (what a hack, huh?)
        if (self.name != "Untitled Plane"):

            # Set properties
            node.set_attributes({
                "name": xml_encode(self.name),
                "active": xml_encode( "%d" % self.active ),
                "shift-x": xml_encode( "%d" % self.shift_x ),
                "shift-y": xml_encode( "%d" % self.shift_y ),
                "slide-x": xml_encode( "%d" % self.slide_x ),
                "slide-y": xml_encode( "%d" % self.slide_y )
            })


        #if (self.name != "Untitled Plane"):
        #    xml = "%s<plane name = '%s' active = '%d' shift-x = '%d' shift-y = '%d' slide-x = '%d' slide-y = '%d' />\n" % (prefix, self.name, self.active, self.shift_x, self.shift_y, self.slide_x, self.slide_y)

        # Return node
        return node


    # I threw this stuff into its own state function because only the master plane will save dig data.
    def save_dig_state(self):

        # Create node
        node = XMLNode("digs")

        # Loop tiles
        for y in range( 0, self.tiles.get_height() ):
            for x in range( 0, self.tiles.get_width() ):

                # Get Trap object for this tile location
                trap = self.traps.read(x, y, default_value = None)

                # Validate Trap object
                if (trap):

                    if ( trap.get_timer() > 0 ):

                        # Add new dig state
                        node.add_node(
                            XMLNode("dig").set_attributes({
                                "tx": xml_encode( "%d" % x ),
                                "ty": xml_encode( "%d" % y ),
                                "tile": xml_encode( "%d" % 0 ), # ? (0 for empty air, I guess...)
                                "tile-backup": xml_encode( "%d" % self.tiles_backup.read(x, y) ),
                                "trap-timer": xml_encode( "%d" % trap.get_timer() ),
                                "trap-timer-delay": xml_encode( "%d" % trap.get_delay() ),
                                "trap-occupants": xml_encode( "%d" % trap.get_occupants() ),
                                "trap-fill-pattern": xml_encode( "%d" % trap.get_fill_pattern() )
                            })
                        )
                        """
                        params = (
                            prefix,
                            x,
                            y,
                            self.tiles_backup.read(x, y),
                            trap.get_timer(),
                            trap.get_delay(),
                            trap.get_occupants(),
                            trap.get_fill_pattern()
                        )

                        xml += "%s<dig tx = '%d' ty = '%d' tile = '0' tile-backup = '%d' trap-timer = '%d' trap-timer-delay = '%d' trap-occupants = '%d' trap-fill-pattern = '%d' />\n" % params
                        """

        # Return node
        return node


    # Same here, I put this in its own state function because only the master plane will use it.
    def save_ai_state(self):

        # Create node
        node = XMLNode("ai")

        log2( "Including random / ghost enemies for debugging..." )

        # Loop... just one genus?  Whatever...
        for genus in (GENUS_ENEMY,):

            # Loop all entities of the current genus
            for entity in self.entities[genus]:

                # Only save state for explicitly named entities
                if (entity.name != ""):

                    # Add node
                    node.add_node(
                        entity.save_ai_state()
                    )
                    #xml += entity.ai_state.compile_memory_string_for_entity(entity, prefix)
                    #xml += entity.compile_memory_string_with_ai_state(prefix)

                #else:
                #    xml += "<random>\n" + entity.compile_memory_string_with_ai_state(prefix) + "</random>\n"

        # Return node
        return node


    # Same deal here; some will overwrite the recall function...
    def load_state(self, node):

        # Load state for this plane, unless this plane is the base "Untitled Plane" (yes, this is hard-coded and brutal!)
        if (
            (self.name != "Untitled Plane") and
            (not self.ignore_previous_state)
        ):

            if ( node.has_attribute("active") ):
                self.active = ( int( node.get_attribute("active") ) == 1 )


            if ( node.has_attribute("shift-x") ):
                self.shift_x = int( node.get_attribute("shift-x") )

            if ( node.has_attribute("shift-y") ):
                self.shift_y = int( node.get_attribute("shift-y") )


            if ( node.has_attribute("slide-x") ):
                self.slide_x = int( node.get_attribute("slide-x") )

            if ( node.has_attribute("slide-y") ):
                self.slide_y = int( node.get_attribute("slide-y") )


    # Set collision values (shared by reference from parent map's parent universe)
    def set_collision_values(self, handle):

        # Set
        self.collision_values_by_tile_index = handle


    # Lock controller
    def lock(self):

        # Increment
        self.lock_count += 1


    # Unlock
    def unlock(self):

        # Decrement
        self.lock_count -= 1


    # Set a plane parameter
    def set_param(self, param, value):

        # Set
        self.params[param] = value


    # Attempt to retrieve a given plane parameter
    def get_param(self, param):

        # Validate
        if (param in self.params):

            return self.params[param]

        # Not found
        else:

            log2( "Warning:  Plane param '%s' does not exist!" % param )
            return None


    def reset_dig_data(self):

        for ty in range( 0, self.tiles.get_height() ):

            for tx in range( 0, self.tiles.get_width() ):

                # Get trap object for tile at this location
                trap = self.traps.read(tx, ty, default_value = None)

                # Validate Trap object
                if (trap):

                    # Needs reset?
                    if ( trap.get_timer() > 0 ):

                        # Restore tile
                        self.tiles.write(
                            tx,
                            ty,
                            self.tiles_backup.read(tx, ty)
                        )

                        # Let's just write a new Trap object with its defaults already set at 0
                        self.traps.write(tx, ty, Trap())


    # Load in dig state data
    def load_dig_state(self, node):

        # Loop dig states
        for ref_dig in node.get_nodes_by_tag("dig"):

            # Get dig properties
            (tx, ty, tile_backup, trap_timer, trap_timer_delay, trap_occupants, trap_fill_pattern) = (
                int( ref_dig.get_attribute("tx") ),
                int( ref_dig.get_attribute("ty") ),
                int( ref_dig.get_attribute("tile-backup") ),
                int( ref_dig.get_attribute("trap-timer") ),
                int( ref_dig.get_attribute("trap-timer-delay") ),
                int( ref_dig.get_attribute("trap-occupants") ),
                int( ref_dig.get_attribute("trap-fill-pattern") )
            )

            log( (tx, ty, tile_backup, trap_timer, trap_timer_delay, trap_occupants, trap_fill_pattern) )

            # Quick validation
            if ( ty < self.tiles.get_height() ):

                if ( tx < self.tiles.get_width() ):

                    # Set tile to empty
                    self.tiles.write(tx, ty, 0)

                    # Keep original tile value for when it refils
                    self.tiles_backup.write(tx, ty, tile_backup)


                    # Write a new Trap object
                    self.traps.write(
                        tx,
                        ty,
                        Trap(
                            timer = trap_timer,
                            delay = trap_timer_delay,
                            occupants = trap_occupants,
                            fill_pattern = trap_fill_pattern
                        )
                    )

                    log( "done at ty = %d, tx = %d" % (ty, tx) )


    # Load in AI state data.
    # Needs a Map object to calculate frozen for data or something like that.  (Hack!)
    def load_ai_state(self, node, m):#p_map, nodes):

        # Loop ai data
        for ref_entity_ai_data in node.get_nodes_by_tag("entity"):

            # Find entity
            entity = m.get_entity_by_name( ref_entity_ai_data.get_attribute("name") )

            # Validate
            if (entity):

                # Load entity AI state
                entity.load_ai_state(ref_entity_ai_data, m)

                # Validate trap state for this enemy
                entity.validate_ai_trapped_state(m)


    def get_width(self):

        return self.tiles.get_width()


    def get_height(self):

        return self.tiles.get_height()


    def set_width(self, w):

        # Sanity (?)
        if (self.get_height() < 1):
            return "No map data set"

        # Must be at least 1 tile wide...
        elif (w < 1):
            return "Must be >= 1"

        else:

            # Resize tile map.  Forget about the others, this only happens in editor mode.  Lousy programming, huH?
            self.tiles.resize(
                width = w,
                height = self.tiles.get_height(),
                default_value = 0                   # Default to blank space tile
            )

            # Flag
            self.updated_dimensions = True

            # Success
            return "ok"


    def set_height(self, h):

        # Sanity (?)
        if (h < 1):
            return "Must be >= 1"

        else:

            # Resize tile map, but don't worry about the others.  We only do this in editor mode.  Still lousy programming.
            self.tiles.resize(
                width = self.tiles.get_width(),
                height = h,
                default_value = 0                   # Default to blank space tile
            )

            # Flag
            self.updated_dimensions = True

            # Success
            return "ok"


    # Pad in extra room on the top/left, or add extra space on the right/bottom
    def pad(self, x = 0, y = 0, w = 0, h = 0):

        # Pad top/left (new rows/columns) first
        self.tiles.pad(px = x, py = y, default_value = 0)
        self.tiles_backup.pad(px = x, py = y, default_value = 0)

        self.traps.pad(px = x, py = y) # Create new trap object as default value


        # Now resize...
        self.tiles.resize(width = w, height = h, default_value = 0)
        self.tiles_backup.resize(width = w, height = h, default_value = 0)

        self.traps.resize(width = w, height = h)

        """
        # Pad the top as necessary
        for j in range(0, y):

            temp_tiles = []
            temp_tiles_backup = []

            temp_timers = []
            temp_timer_delays = []

            temp_occupants = []
            temp_fill_patterns = []

            # Might be a 0-wide map
            if (len(self.tiles) > 0):

                for i in range(0, len(self.tiles[0])):

                    temp_tiles.append(0)
                    temp_tiles_backup.append(0)

                    temp_timers.append(0)
                    temp_timer_delays.append(0)

                    temp_occupants.append(0)
                    temp_fill_patterns.append(0)

            # Insert as first row
            self.tiles.insert(0, temp_tiles)
            self.tiles_backup.insert(0, temp_tiles_backup)

            self.trap_timers.insert(0, temp_timers)
            self.trap_timer_delays.insert(0, temp_timer_delays)

            self.trap_occupants.insert(0, temp_occupants)
            self.trap_fill_patterns.insert(0, temp_fill_patterns)

        # Pad the bottom
        for j in range(0, h):

            temp_tiles = []
            temp_tiles_backup = []

            temp_timers = []
            temp_timer_delays = []

            temp_occupants = []
            temp_fill_patterns = []

            if (len(self.tiles) > 0):

                for i in range(0, len(self.tiles[0])):

                    temp_tiles.append(0)
                    temp_tiles_backup.append(0)

                    temp_timers.append(0)
                    temp_timer_delays.append(0)

                    temp_occupants.append(0)
                    temp_fill_patterns.append(0)

            self.tiles.append(temp_tiles)
            self.tiles_backup.append(temp_tiles_backup)

            self.trap_timers.append(temp_timers)
            self.trap_timer_delays.append(temp_timer_delays)

            self.trap_occupants.append(temp_occupants)
            self.trap_fill_patterns.append(temp_fill_patterns)

        # Pad the left as necessary
        for j in range(0, x):

            for i in range(0, len(self.tiles)):

                # Insert as first column
                self.tiles[i].insert(0, 0)
                self.tiles_backup[i].insert(0, 0)

                self.trap_timers[i].insert(0, 0)
                self.trap_timer_delays[i].insert(0, 0)

                self.trap_occupants[i].insert(0, 0)
                self.trap_fill_patterns[i].insert(0, 0)

        # Pad the right
        for j in range(0, w):

            for i in range(0, len(self.tiles)):

                # Insert as first column
                self.tiles[i].append(0)
                self.tiles_backup[y].append(0)

                self.trap_timers[y].append(0)
                self.trap_timer_delays[y].append(0)

                self.trap_occupants[y].append(0)
                self.trap_fill_patterns[y].append(0)
        """

    def handle_message(self, message, param, p_map):

        # Add a new hotspot for this entity
        if (message == "activate"):

            self.active = True

            # map state has changed
            p_map.update_master_plane()

            return True

        # Clear all hotspots (likely to make room for new ones)
        elif (message == "deactivate"):

            self.active = False

            # map state has changed
            p_map.update_master_plane()

            return True

        # Fade out?
        elif (message == "fade-out"):

            self.alpha_controller.dismiss()

            self.alpha_controller.process()

            # Don't overshoot
            if ( not self.alpha_controller.is_visible() ):

                # Inactive once faded out...
                self.active = False

                # Rebuild master plane
                p_map.update_master_plane()

                # Done!
                return True

            else:

                # Not done fading out...
                return False

        # Fade in?
        elif (message == "fade-in"):

            # Plane must be active now if it's fading in...
            self.active = True

            self.alpha_controller.summon()

            self.alpha_controller.process()

            if ( self.alpha_controller.get_interval() >= 1 ):

                # Rebuild master plane
                p_map.update_master_plane()

                # Done!
                return True

            else:

                # Not done fading in...
                return False

    def slide(self, dx, dy):

        self.x += dx
        self.y += dy

    def randomize_base_tile(self, tile, randomizer_range):

        for y in range( 0, self.tiles.get_height() ):
            for x in range( 0, self.tiles.get_width() ):

                if ( self.tiles.read(x, y) in range(tile, tile + randomizer_range) ):

                    self.tiles.write(x, y, (tile + random.randint(0, randomizer_range)))

    def set_tile(self, tx, ty, value):

        self.tiles.write(tx, ty, value)


    def set_tile_backup(self, tx, ty, value):

        self.tiles_backup.write(tx, ty, value)


    def get_tile(self, tx, ty):

        return self.tiles.read(tx, ty, default_value = 0)


    def get_tile_backup(self, tx, ty):

        return self.tiles_backup.read(tx, ty, default_value = 0)


    def build_gold_cache(self):

        self.gold_cache = []

        # Default all to nothing
        for y in range( 0, self.tiles.get_height() ):

            temp_row = []

            for x in range( 0, self.tiles.get_width() ):
                temp_row.append([])

            self.gold_cache.append(temp_row)

        # Now loop through all gold entities and put them in their places...
        for gold in self.entities[GENUS_GOLD]:

            (tx, ty) = (
                int( gold.get_x() / TILE_WIDTH ),
                int( gold.get_y() / TILE_HEIGHT )
            )

            if (ty >= 0 and ty < len(self.gold_cache)):

                if (tx >= 0 and tx < len(self.gold_cache[ty])):

                    self.gold_cache[ty][tx].append(gold.name)

    def shift_to_target(self, x_target, y_target, speed, ghost, affected_entities, p_map):

        #print "target for %s:  " % self.name, (x_target, y_target)

        # I'll use these values to offset affected entities.
        # When the plane reaches its destination, it might overshoot it;
        # after I correct the alignment, I'll want to use that correction
        # as the movement speed for each affected entity.
        (ax, ay) = (speed, speed)

        prior_x = (self.x * TILE_WIDTH) + self.shift_x
        prior_y = (self.y * TILE_HEIGHT) + self.shift_y


        """ Begin clamping - do not let planes shift off of the map """
        # Do not target off left edge of map
        if (x_target < 0):

            # Clamp
            x_target = 0

        # Do not target off right edge of map
        elif (x_target > ( (p_map.get_width() * TILE_WIDTH) - (self.get_width() * TILE_WIDTH) )):

            # Clamp
            x_target = ( (p_map.get_width() * TILE_WIDTH) - (self.get_width() * TILE_WIDTH) )


        # Do not target off top edge of map
        if (y_target < 0):

            # Clamp
            y_target = 0

        # Do not target off bottom edge of map
        elif (y_target > ( (p_map.get_height() * TILE_HEIGHT) - (self.get_height() * TILE_HEIGHT) )):

            # Clamp
            y_target = ( (p_map.get_height() * TILE_HEIGHT) - (self.get_height() * TILE_HEIGHT) )
        """ End clamping """


        # x-axis
        if (prior_x + self.dx > x_target):

            self.dx -= speed


            # If this plane can collide with other planes, let's check that first...
            if (not ghost):

                # Get the tile position we'll start checking
                (lx, ly) = (
                    int( ( ( (self.x * TILE_WIDTH) + self.shift_x) + self.dx ) / TILE_WIDTH ),
                    int( ( ( (self.y * TILE_HEIGHT) + self.shift_y) + self.dy ) / TILE_HEIGHT )
                )

                collides = False

                for y in range( 0, self.tiles.get_height() ):
                    for x in range( 0, self.tiles.get_width() ):

                        if ( (self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE))  and  (p_map.master_plane.check_collision(lx + x, ly + y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)) ):
                            collides = True


                # If the plane collides, then the ride is over.  Start by setting the plane's position...
                if (collides):

                    final_x = (lx + 1) * TILE_WIDTH

                    self.shift_x += int(final_x - prior_x)

                    # We're done here.
                    return True


            # First, apply friction to any affected entity
            a = 0

            self.shift_stowaways = self.sort_entities_by_x_asc(self.shift_stowaways)

            while ( a < len(self.shift_stowaways) ):

                # Try to move the affected entity
                result = self.shift_stowaways[a].nudge(-ax, 0, p_map)

                # If the entity hit a wall or another entity, then
                # they essentially "fall off" of this plane.
                if (result == False):

                    self.shift_stowaways.pop(a)
                    log( "bye bye" )

                else:
                    a += 1


            # Even ghost planes will push entities around.  Let's check every entity for collision against this moving plane...
            (lx, ly) = (
                (prior_x + self.dx),
                (prior_y + self.dy)
            )

            for y in range( 0, self.tiles.get_height() ):
                for x in range( 0, self.tiles.get_width() ):

                    #ox = self.tiles.read(x, y) % TILESHEET_TILES_WIDE
                    #oy = int(self.tiles.read(x, y) / TILESHEET_TILES_WIDE)

                    if ( self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)):

                        lr = (lx + (x * TILE_WIDTH), ly + (y * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT)

                        for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

                            for entity in p_map.master_plane.entities[genus]:

                                if ( not (entity in self.shift_stowaways) ):

                                    # If we've pushed into the player, adjust the player's position...
                                    if ( intersect(entity.get_rect(), lr) ):

                                        # Cascade the player (and any entities behind her/him)
                                        entity.cascade_to_position(lr[0], None, DIR_LEFT, p_map)

                                        log( "'%s' intersects at (%d, %d)" % (entity.name, x, y) )


        elif (prior_x + self.dx < x_target):

            self.dx += speed


            # If this plane can collide with other planes, let's check that first...
            if (not ghost):

                # Get the tile position we'll start checking
                (lx, ly) = (
                    int( ( ( (self.x * TILE_WIDTH) + self.shift_x) + self.dx - 1 ) / TILE_WIDTH ),
                    int( ( ( (self.y * TILE_HEIGHT) + self.shift_y) + self.dy ) / TILE_HEIGHT )
                )

                collides = False

                for y in range( 0, self.tiles.get_height() ):
                    for x in range( 0, self.tiles.get_width() ):

                        if ( (self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE))  and  (p_map.master_plane.check_collision(lx + x + 1, ly + y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)) ):
                            collides = True

                # If the plane collides, then the ride is over.  Start by setting the plane's position...
                if (collides):

                    final_x = (lx - 0) * TILE_WIDTH

                    self.shift_x += int(final_x - prior_x)

                    # We're done here.
                    return True


            # First, apply friction to any affected entity
            a = 0

            self.shift_stowaways = self.sort_entities_by_x_desc(self.shift_stowaways)

            while ( a < len(self.shift_stowaways) ):

                # Try to move the affected entity
                result = self.shift_stowaways[a].nudge(ax, 0, p_map)

                # If the entity hit a wall or another entity, then
                # they essentially "fall off" of this plane.
                if (result == False):

                    self.shift_stowaways.pop(a)

                else:
                    a += 1


            # Even ghost planes will push entities around.  Let's check every entity for collision against this moving plane...
            (lx, ly) = (
                (prior_x + self.dx),
                (prior_y + self.dy)
            )

            for y in range( 0, self.tiles.get_height() ):
                for x in range( 0, self.tiles.get_width() ):

                    #ox = self.tiles.read(x, y) % TILESHEET_TILES_WIDE
                    #oy = int(self.tiles.read(x, y) / TILESHEET_TILES_WIDE)

                    if ( self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)):

                        lr = (lx + (x * TILE_WIDTH), ly + (y * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT)

                        for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

                            for entity in p_map.master_plane.entities[genus]:

                                # If we've pushed into the player, adjust the player's position...
                                if ( intersect(entity.get_rect(), lr) ):

                                    # Cascade the player (and any entities behind her/him)
                                    entity.cascade_to_position(lr[0] + lr[2], None, DIR_RIGHT, p_map)


        # y-axis
        if (prior_y + (self.dy) > y_target):

            log( "Moving up:  ", (prior_y, self.dy, cf(self.dy), y_target) )

            self.dy -= cf(speed)


            # Don't overshoot; correct float errors
            if (prior_y + cf(self.dy) <= y_target):
                self.dy = y_target - prior_y

                log( "Reached destination... self.dy = ", self.dy )



            # If this plane can collide with other planes, let's check that first...
            if (not ghost):

                # Get the tile position we'll start checking
                (lx, ly) = (
                    int( ( ( (self.x * TILE_WIDTH) + self.shift_x) + cf(self.dx) ) / TILE_WIDTH ),
                    int( ( ( (self.y * TILE_HEIGHT) + self.shift_y) + cf(self.dy) ) / TILE_HEIGHT )
                )

                log( "(lx, ly) = ", (lx, ly) )

                collides = False

                for y in range( 0, self.tiles.get_height() ):
                    for x in range( 0, self.tiles.get_width() ):

                        if ( (self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE))  and  (p_map.master_plane.check_collision(lx + x, ly + y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)) ):
                            collides = True

                            """
                            log( "Colliding tile at (%d, %d) has value %d" % (lx + x, ly + y, self.tiles.read(x, y)) )
                            for q in p_map.master_plane.tiles:
                                for w in range(0, len(q)):
                                    log( "%d " % q[w], )
                                log( "" )
                            """


                # If the plane collides, then the ride is over.  Start by setting the plane's position...
                if (collides):

                    final_y = (ly + 1) * TILE_HEIGHT

                    self.shift_y += int(final_y - prior_y)

                    #print 5/0
                    log( "Hit map tile collision" )

                    # We're done here.
                    return True


            # First, apply friction to any affected entity
            a = 0

            while ( a < len(self.shift_stowaways) ):

                # Try to move the affected entity
                result = self.shift_stowaways[a].nudge(0, -ay, p_map)

                # If the entity hit a wall or another entity, then
                # they essentially "fall off" of this plane.
                if (result == False):
                    self.shift_stowaways.pop(a)

                else:
                    z = self.shift_stowaways[a]
                    log( z.name, " = ", z.y, "(via %s)" % self.name )
                    a += 1


            # Even ghost planes will push entities around.  Let's check every entity for collision against this moving plane...
            (lx, ly) = (
                (prior_x + (self.dx)),
                (prior_y + cf(self.dy))
            )

            for y in range( 0, self.tiles.get_height() ):
                for x in range( 0, self.tiles.get_width() ):

                    #ox = self.tiles.read(x, y) % TILESHEET_TILES_WIDE
                    #oy = int(self.tiles.read(x, y) / TILESHEET_TILES_WIDE)

                    if ( self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)):

                        lr = (lx + (x * TILE_WIDTH), ly + (y * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT)

                        for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

                            for entity in p_map.master_plane.entities[genus]:

                                if ( not (entity in self.shift_stowaways) ):

                                    # If we've pushed into the player, adjust the player's position...
                                    if ( intersect(entity.get_rect(), lr) ):

                                        # Cascade the player (and any entities behind her/him)
                                        entity.cascade_to_position(None, lr[1], DIR_UP, p_map)


        elif (prior_y + self.dy < y_target):

            self.dy += cf(speed)


            # Don't overshoot; fix floating errors
            if (prior_y + cf(self.dy) >= y_target):
                self.dy = y_target - prior_y


            #print self.dy


            # If this plane can collide with other planes, let's check that first...
            if (not ghost):

                # Get the tile position we'll start checking
                (lx, ly) = (
                    int( ( ( (self.x * TILE_WIDTH) + self.shift_x) + self.dx ) / TILE_WIDTH ),
                    int( ( ( (self.y * TILE_HEIGHT) + self.shift_y) + self.dy - 1 ) / TILE_HEIGHT )
                )

                collides = False

                for y in range( 0, self.tiles.get_height() ):
                    for x in range( 0, self.tiles.get_width() ):

                        if ( (self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE))  and  (p_map.master_plane.check_collision(lx + x, ly + y + 1) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE)) ):
                            collides = True

                # If the plane collides, then the ride is over.  Start by setting the plane's position...
                if (collides):

                    log( self.name )
                    #print 5/0

                    final_y = (ly - 0) * TILE_HEIGHT

                    self.shift_y += int(final_y - prior_y)

                    # We're done here.
                    return True


            # First, apply friction to any affected entity
            a = 0

            while (a < len(self.shift_stowaways)):

                # Try to move the affected entity
                result = self.shift_stowaways[a].nudge(0, ay, p_map)

                # If the entity hit a wall or another entity, then
                # they essentially "fall off" of this plane.
                if (result == False):
                    #print "'%s' falls off plane '%s!!!'" % (self.shift_stowaways[a].name, self.name)
                    self.shift_stowaways.pop(a)

                else:
                    a += 1


            # Even ghost planes will push entities around.  Let's check every entity for collision against this moving plane...
            (lx, ly) = (
                (prior_x + self.dx),
                (prior_y + self.dy)
            )

            for y in range( 0, self.tiles.get_height() ):
                for x in range( 0, self.tiles.get_width() ):

                    #ox = self.tiles.read(x, y) % TILESHEET_TILES_WIDE
                    #oy = int(self.tiles.read(x, y) / TILESHEET_TILES_WIDE)

                    if ( self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY, COLLISION_BRIDGE) ):

                        lr = (lx + (x * TILE_WIDTH), ly + (y * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT)

                        for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

                            for entity in p_map.master_plane.entities[genus]:

                                if ( not (entity in self.shift_stowaways) ):

                                    # If we've pushed into the player, adjust the player's position...
                                    if ( intersect(entity.get_rect(), lr) ):

                                        # Cascade the player (and any entities behind her/him)
                                        entity.cascade_to_position(None, lr[1] + lr[3], DIR_DOWN, p_map)


        # Are we there yeti?  (return True for complete)
        if ( (prior_x + self.dx == x_target) and (prior_y + self.dy == y_target) ):

            # Let's remember the current position's shift values...
            self.shift_x += self.dx
            self.shift_y += self.dy

            # For any stowaway that is trapped, we need to adjust the trap exception's location...
            for entity in self.shift_stowaways:

                if (entity.ai_state.ai_is_trapped):

                    entity.ai_state.ai_trap_exception = (
                        entity.ai_state.ai_trap_exception[0] + int(self.dx / TILE_WIDTH),
                        entity.ai_state.ai_trap_exception[1] + int(self.dy / TILE_HEIGHT)
                    )

            return True


        else:
            return False

    def planar_slide(self, slide, speed, trigger = None, p_map = None, amount = -1):

        # Targeted slides must calculate the slide direction at runtime,
        # checking the current slide value against the target trigger's location.
        if (trigger):

            t = p_map.get_trigger_by_name(trigger)

            if (t):

                (y1, y2) = (
                    self.slide_y,
                    (t.y * TILE_HEIGHT) - ( (self.y * TILE_HEIGHT) + self.shift_y )
                )

                if (y1 < y2):
                    slide = DIR_DOWN

                else:
                    slide = DIR_UP


        if (slide == DIR_UP):

            # Slide the plane...
            target = 0

            # Specified slide distance?
            if (amount >= 0):

                # Obey
                target = amount


            if (trigger):

                t = p_map.get_trigger_by_name(trigger)

                if (t):
                    target = (t.y * TILE_HEIGHT) - ( (self.y * TILE_HEIGHT) + self.shift_y )


            self.slide_y -= speed

            # Don't overshoot
            if (self.slide_y < target):

                self.slide_y = target


            return (self.slide_y == target)


        elif (slide == DIR_DOWN):

            # Slide to full height...
            target = (self.get_height() * TILE_HEIGHT)

            # Specified slide distance?
            if (amount >= 0):

                # Obey
                target = amount


            if (trigger):

                t = p_map.get_trigger_by_name(trigger)

                if (t):
                    target = (t.y * TILE_HEIGHT) - ( (self.y * TILE_HEIGHT) + self.shift_y )


            self.slide_y += speed

            # Don't overshoot
            if (self.slide_y > target):

                self.slide_y = target


            # Check for any entity in the way...
            prior_x = (self.x * TILE_WIDTH) + self.shift_x
            prior_y = (self.y * TILE_HEIGHT) + self.shift_y

            (lx, ly) = (
                (prior_x),
                (prior_y)
            )

            # What area of effect does the sliding plane have?
            lrBound = (prior_x, prior_y, (self.get_width() * TILE_WIDTH), self.slide_y)

            for y in range( 0, self.tiles.get_height() ):
                for x in range( 0, self.tiles.get_width() ):

                    #ox = self.tiles.read(x, y) % TILESHEET_TILES_WIDE
                    #oy = int(self.tiles.read(x, y) / TILESHEET_TILES_WIDE)

                    if ( self.check_collision(x, y) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_DEADLY) ):

                        lr = (lx + (x * TILE_WIDTH), ly + (y * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT)

                        for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

                            for entity in p_map.master_plane.entities[genus]:

                                # If we've pushed into the player, adjust the player's position...
                                if ( intersect(entity.get_rect(), lr) and intersect(entity.get_rect(), lrBound) ):

                                    # Cascade the player (and any entities behind her/him)
                                    entity.cascade_to_position(None, lrBound[1] + lrBound[3], DIR_DOWN, p_map)

            return (self.slide_y == target)

    def get_tile_index_collision_type(self, tile):

        #ty = int(tile / TILESHEET_TILES_WIDE)
        #tx = int(tile % TILESHEET_TILES_WIDE)

        try:
            #return TILESHEET_COLLISION_VALUES[ty][tx]
            return self.collision_values_by_tile_index[tile]

        except:
            return COLLISION_NONE

    def check_collision(self, tx, ty, strictly_within_level = False):

        if ( ty >= 0 and ty < self.tiles.get_height() ):

            if ( tx >= 0 and tx < self.tiles.get_width() ):
                return self.get_tile_index_collision_type( self.tiles.read(tx, ty) )


        # Must have been out of bounds...
        if ( self.bounding_plane and (not strictly_within_level) ):

            if ( ty >= -COLLISION_BOUNDARY_SIZE and ty < ( self.tiles.get_height() + COLLISION_BOUNDARY_SIZE ) ):

                if ( tx >= -COLLISION_BOUNDARY_SIZE and tx <= ( self.tiles.get_width() + COLLISION_BOUNDARY_SIZE ) ):

                    # Shift ahead by boundary size to align at (0, 0) on the bounding plane
                    (bx, by) = (tx + COLLISION_BOUNDARY_SIZE, ty + COLLISION_BOUNDARY_SIZE)

                    #log( "bx, by:  ", (bx, by) )
                    return self.get_tile_index_collision_type( self.bounding_plane.tiles.read(bx, by) )

        else:

            # Out-of-bounds error?  No collision, then...
            return COLLISION_NONE


        return COLLISION_NONE

    # This version pretends that dug tiles are solid tiles...
    def check_faux_collision(self, tx, ty):

        if ( ty >= 0 and ty < self.tiles.get_height() ):

            if ( tx >= 0 and tx < self.tiles.get_width() ):

                if ( self.traps.read(tx, ty).get_timer() > 0 ):
                    return COLLISION_DIGGABLE

                else:
                    return self.get_tile_index_collision_type( self.tiles.read(tx, ty) )

    def check_collision_value_exists_in_rect(self, r, values, exception = None):

        tx1 = int(r[0] / TILE_WIDTH)
        ty1 = int(r[1] / TILE_HEIGHT)

        tx2 = int( (r[0] + r[2] - 1) / TILE_WIDTH)
        ty2 = int( (r[1] + r[3] - 1) / TILE_HEIGHT)

        points = (
            (tx1, ty1),
            (tx2, ty1),
            (tx1, ty2),
            (tx2, ty2)
        )

        for p in points:

            if (self.check_collision(p[0], p[1]) in values):
                return True

            elif (exception == p):
                return True

        return False

    def check_faux_collision_value_exists_in_rect(self, r, values, exception = None):

        tx1 = int(r[0] / TILE_WIDTH)
        ty1 = int(r[1] / TILE_HEIGHT)

        tx2 = int( (r[0] + r[2] - 1) / TILE_WIDTH)
        ty2 = int( (r[1] + r[3] - 1) / TILE_HEIGHT)

        points = (
            (tx1, ty1),
            (tx2, ty1),
            (tx1, ty2),
            (tx2, ty2)
        )

        for p in points:

            if (self.check_faux_collision(p[0], p[1]) in values):

                if (not (exception == p)):
                    return True

        return False

    def get_gold_in_rect(self, r):

        tx1 = int(r[0] / TILE_WIDTH)
        ty1 = int(r[1] / TILE_HEIGHT)

        tx2 = int( (r[0] + r[2] - 1) / TILE_WIDTH)
        ty2 = int( (r[1] + r[3] - 1) / TILE_HEIGHT)

        points = (
            (tx1, ty1),
            (tx2, ty1),
            (tx1, ty2),
            (tx2, ty2)
        )

        results = []

        for (tx, ty) in points:

            if (ty >= 0 and ty < len(self.gold_cache)):

                if (tx >= 0 and tx < len(self.gold_cache[ty])):

                    results.extend(self.gold_cache[ty][tx])

        return results

    # Called when an enemy falls into a trap and drops his gold
    def add_gold_to_cache(self, entity):

        (tx, ty) = (
            int( entity.get_x() / TILE_WIDTH ),
            int( entity.get_y() / TILE_HEIGHT )
        )

        if (ty >= 0 and ty < len(self.gold_cache)):

            if (tx >= 0 and tx < len(self.gold_cache[ty])):

                self.gold_cache[ty][tx].append(entity.name)

    def remove_gold_from_rect_by_name(self, r, name):

        tx1 = int(r[0] / TILE_WIDTH)
        ty1 = int(r[1] / TILE_HEIGHT)

        tx2 = int( (r[0] + r[2] - 1) / TILE_WIDTH)
        ty2 = int( (r[1] + r[3] - 1) / TILE_HEIGHT)

        points = (
            (tx1, ty1),
            (tx2, ty1),
            (tx1, ty2),
            (tx2, ty2)
        )

        for (tx, ty) in points:

            if (ty >= 0 and ty < len(self.gold_cache)):

                if (tx >= 0 and tx < len(self.gold_cache[ty])):

                    if (name in self.gold_cache[ty][tx]):

                        pos = self.gold_cache[ty][tx].index(name)
                        self.gold_cache[ty][tx].pop(pos)

    def check_collision_in_rect(self, r):
        return self.check_collision_value_exists_in_rect(r, (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_BRIDGE, COLLISION_SPIKES_LEFT, COLLISION_SPIKES_RIGHT))

    def check_deadly_collision_in_rect_from_direction(self, r, direction):

        if (direction == DIR_LEFT):
            return self.check_collision_value_exists_in_rect(r, (COLLISION_SPIKES_LEFT,))

        elif (direction == DIR_RIGHT):
            return self.check_collision_value_exists_in_rect(r, (COLLISION_SPIKES_RIGHT,))

        else:
            return False

    def check_fall_collision_in_rect(self, r, exception = None):
        return self.check_collision_value_exists_in_rect(r, (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_BRIDGE, COLLISION_LADDER, COLLISION_SPIKES_LEFT, COLLISION_SPIKES_RIGHT), exception)

    def check_deadly_fall_collision_in_rect(self, r, exception = None):
        return self.check_collision_value_exists_in_rect(r, (COLLISION_DEADLY,), exception)

    def check_ladder_exists_in_rect(self, r):
        return self.check_collision_value_exists_in_rect(r, (COLLISION_LADDER,))

    def check_monkeybar_exists_in_rect(self, r):
        return self.check_collision_value_exists_in_rect(r, (COLLISION_MONKEYBAR,))


    # See if a ladder OR a monkeybar exists in a given rect.
    # We'll use this, for instance, when the player pressed DOWN and we want to see if they are facing + touching a downward-movement tile.
    def check_ladder_or_monkeybar_exists_in_rect(self, r):

        # Check collision value
        return self.check_collision_value_exists_in_rect(
            r,
            (COLLISION_LADDER, COLLISION_MONKEYBAR)
        )


    def contains_trapped_entity(self, entity):

        # An easy test...
        if (entity.ai_state.ai_trap_exception == None):
            return False


        # Calculate relative top-left origin point for this plane; account for previous planar shifts.
        (rx, ry) = (
            self.x + int(self.shift_x / TILE_WIDTH),
            self.y + int(self.shift_y / TILE_HEIGHT)
        )

        # Check each relative tile...
        for y in range( 0, self.tiles.get_height() ):

            for x in range( 0, self.tiles.get_width() ):

                # We only care about tiles in this plane that exist
                if (self.tiles_backup[y][x] > 0):

                    # Is the entity trapped here?
                    if (entity.ai_state.ai_trap_exception == (rx + x, ry + y)):
                        return True


        # I guess he isn't trapped in this plane...
        return False

    def get_entity_by_name(self, name):

        for genus in self.entities:

            for entity in self.entities[genus]:

                if (entity.name == name):

                    return entity

        return None

    def spotlight_entity_by_type(self, target_entity, genus):

        for entity in self.entities[genus]:

            if (entity == target_entity):

                (a, b) = (
                    self.entities[genus].index(entity),
                    len( self.entities[genus] ) - 1
                )

                (self.entities[genus][a], self.entities[genus][b]) = (self.entities[genus][b], self.entities[genus][a])

                #self.entities[genus].append( self.entities[genus].pop(pos) )


    # Count the number of enemies in a given region
    def count_enemies_in_rect(self, r, exceptions = []):

        # Assume
        count = 0

        # Check all enemies
        for e in self.entities[GENUS_ENEMY]:

            # Ignore exceptions
            if ( ( not (e in exceptions) ) and ( e.is_touchable() ) ):

                # Intersection test
                if ( intersect(r, e.get_rect()) ):

                    # Increment counter
                    count += 1

        # Return total matches
        return count


    def count_entities_in_rect(self, r, exceptions = []):

        count = 0

        for genus in (GENUS_PLAYER, GENUS_ENEMY):

            for entity in self.entities[genus]:

                if ( ( not (entity in exceptions) ) and ( entity.is_touchable() ) ):

                    if ( intersect(r, entity.get_rect()) ):

                        count += 1

        return count


    # Convenience function that simply checks a gainst player / enemy entity types
    def query_interentity_collision_for_entity(self, ref_entity):

        # Forward
        return self.query_interentity_collision_for_entity_against_entity_types( (GENUS_ENEMY, GENUS_PLAYER), ref_entity)


    # For a given entity, find any other entity that currently intersects
    def query_interentity_collision_for_entity_against_entity_types(self, entity_types, ref_entity):

        # Track results
        results = IntersectionQueryResults()


        # Only entities that can collide with other entities will have results...
        if ( not (ref_entity.genus in NONCOLLIDING_ENTITY_TYPES) ):

            entities = []

            # Loop through each entity type we care about
            for genus in entity_types:

                # Loop each entity in this genus
                for entity in self.entities[genus]:

                    # Don't test against ourself, and only test against "touchable" entities
                    if ( ( not (ref_entity == entity) ) and ( entity.is_touchable() ) ):

                        # Finally, the intersection test!
                        result = ref_entity.intersects_entity(entity)

                        # Intersects?
                        if (result):# != (0, 0)):

                            # I'm going to try disabling this "instant add" and instead add if the
                            # intersect_x / intersecT_y calculations evaluate to True.
                            """
                            # Add the result
                            results.add(entity)
                            """

                            # For some reason I require some certain amount of overlap before I do this?  is this right?
                            intersect_x = min(
                                abs( (ref_entity.x + ref_entity.width) - entity.get_x() ),
                                abs( (entity.get_x() + entity.width) - ref_entity.x )
                            )

                            intersect_y = min(
                                abs( (ref_entity.y + ref_entity.height) - entity.get_y() ),
                                abs( (entity.get_y() + entity.height) - ref_entity.y )
                            )

                            # Add collision match
                            if ( (intersect_x >= ref_entity.speed) or (intersect_y >= ref_entity.speed) ):
                                #entity.handle_entity_touch(ref_entity)
                                results.add(entity)

                            # ??????????
                            else:
                                results.add(entity)
                                log2( "< speed collision added (does this matter?)" )


        # Return query results
        return results


    def sort_entities_by_x_asc(self, entities):

        # Final output
        ordered = []

        # Let's create a series of tuples... x position, entity object
        tuples = []

        for entity in entities:
            tuples.append( (entity.get_x(), entity) )

        # Order by x value
        tuples.sort()

        # Now, based on that order, determine our output...
        for (x, entity) in tuples:
            ordered.append(entity)

        return ordered

    def sort_entities_by_y_asc(self, entities):

        # Final output
        ordered = []

        # Let's create a series of tuples... x position, entity object
        tuples = []

        for entity in entities:
            tuples.append( (entity.get_y(), entity) )

        # Order by y value
        tuples.sort()

        # Now, based on that order, determine our output...
        for (y, entity) in tuples:
            ordered.append(entity)

        return ordered

    def sort_entities_by_x_desc(self, entities):

        ordered = self.sort_entities_by_x_asc(entities)
        ordered.reverse()

        return ordered

    def sort_entities_by_y_desc(self, entities):

        ordered = self.sort_entities_by_y_asc(entities)
        ordered.reverse()

        return ordered

    def get_choke_points_in_tile_coords(self, x, y, allow_fall = False):

        (tx, ty) = (
            int(x / TILE_WIDTH),
            int(y / TILE_HEIGHT)
        )

        # Default to the entire width of the level
        (choke_left, choke_right) = (0, self.tiles.get_width())


        # Find the left choke point
        for i in range(tx, -1, -1):

            # Can't get past walls...
            if (self.check_collision(i, ty) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE)):
                choke_left = i
                break

            # We also can't walk over empty spaces (unless there's a monkey bar...)
            elif (not ( self.check_faux_collision(i, ty + 1) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_LADDER, COLLISION_BRIDGE) )):

                if (not ( self.check_collision(i, ty) in (COLLISION_MONKEYBAR, COLLISION_LADDER) )):

                    if (not allow_fall):
                        choke_left = i
                        break


        # Find the right choke point
        for i in range(tx + 1, self.tiles.get_width(), 1):

            # Can't get past walls...
            if (self.check_collision(i, ty) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE)):
                choke_right = i
                break

            # We also can't walk over empty spaces (unless there's a monkey bar...)
            elif (not ( self.check_faux_collision(i, ty + 1) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_LADDER, COLLISION_BRIDGE) )):

                if (not ( self.check_collision(i, ty) in (COLLISION_MONKEYBAR, COLLISION_LADDER) )):

                    if (not allow_fall):
                        choke_right = i
                        break


        return (choke_left, choke_right)

    def get_drop_points_in_tile_coords(self, x, y):

        (tx, ty) = (
            int(x / TILE_WIDTH),
            int(y / TILE_HEIGHT)
        )

        # Default to no drop points
        (drop_left, drop_right) = (None, None)


        # Find the left drop point
        for i in range(tx, -1, -1):

            # Can't get past walls...
            if (self.check_faux_collision(i, ty + 1) in (COLLISION_NONE, COLLISION_MONKEYBAR)):
                drop_left = i
                break


        # Find the right drop point
        for i in range(tx + 1, self.tiles.get_width(), 1):

            # Can't get past walls...
            if (self.check_faux_collision(i, ty + 1) in (COLLISION_NONE, COLLISION_MONKEYBAR)):
                drop_right = i
                break


        return (drop_left, drop_right)

    def dig_tile_at_tile_coords(self, tx, ty, purge = False, scripted_dig = False, duration_multiplier = 1, force_dig = False):

        result = self.check_collision(tx, ty, strictly_within_level = True)

        if ( (result == COLLISION_DIGGABLE) or (force_dig) ):

            # Can't dig beneath ladders/other tiles, unless it's a purely scripted event...
            if ( (scripted_dig == True) or (self.check_collision(tx, ty - 1, strictly_within_level = True) in (COLLISION_NONE, COLLISION_MONKEYBAR, COLLISION_BRIDGE)) ):

                # Sometimes we want to permanently destroy a tile...
                if (purge):

                    self.tiles.write(tx, ty, 0)
                    self.tiles_backup.write(tx, ty, 0)

                    # Reset any trap data by writing a new, default Trap object
                    self.traps.write( tx, ty, Trap() )

                    # Return an empty result to prevent particle effect (?)
                    return DIG_RESULT_EMPTY

                else:

                    if ( self.tiles.read(tx, ty) > 0 ):

                        #self.tiles_backup[ty][tx] = self.tiles.read(tx, ty)

                        self.tiles.write(tx, ty, 0)

                        # Create a new Trap object at this location
                        self.traps.write(
                            tx,
                            ty,
                            Trap(
                                timer = int( DIG_MAX_TIME * duration_multiplier ),
                                delay = 0,
                                occupants = 0,
                                fill_pattern = DIG_PATTERN_IDS[ random.randint(0, len(DIG_PATTERN_IDS) - 1) ]
                            )
                        )

                        # Great success!
                        return DIG_RESULT_SUCCESS

                    # Can't dig the 0 tile, ever, even from a script
                    else:
                        return DIG_RESULT_EMPTY


            else:
                return DIG_RESULT_EMPTY

        elif (result == COLLISION_UNDIGGABLE):

            return DIG_RESULT_UNDIGGABLE

        else:
            return DIG_RESULT_EMPTY

    def trap_exists_at_tile_coords(self, tx, ty, exception):

        # Get trap object
        trap = self.traps.read(tx, ty, default_value = None)

        # Validate
        if (trap):

            # Timer active?
            if ( trap.get_timer() > 0 ):

                # No occupants?
                if ( trap.get_occupants() == 0 ):

                    # Excepted tile location?
                    if ( exception == (tx, ty) ):

                        # Get out of jail free, for now...
                        return False

                    # Otherwise, go ahead and reserve this trap...
                    else:

                        # Set as occupied
                        trap.set_occupants(1)

                        # Trap does exist here...
                        return True

        # Default
        return False


    def set_matrix_frame_delay(self, frame_delay):

        self.matrix_step = 0
        self.matrix_step_max = frame_delay


    def process(self, control_center, universe):

        # Fetch input controller
        input_controller = control_center.get_input_controller()

        # Fetch network controller
        network_controller = control_center.get_network_controller()


        # Fetch local player
        local_player = self.get_entity_by_name( "player%s" % universe.get_session_variable("core.player-id").get_value() )
        #print local_player

        for player in self.entities[GENUS_PLAYER]:

            # Process player logic
            #player.process(network_controller, universe, p_map, session)
            player.process(control_center, universe)

            # Handle any player input
            if (player == local_player):

                if ( universe.is_soft_locked() ):

                    """ Debug """
                    # Here's a debug version of the standard code...
                    if ( INPUT_DEBUG in input_controller.get_gameplay_input() ):
                        logn( "map debug gameplay-input", input_controller.get_gameplay_input() )

                        # Hack in debug input command
                        player.handle_user_input( [INPUT_DEBUG], control_center, universe )#[], network_controller, universe, p_map, session)

                    else:
                        player.handle_user_input( [], control_center, universe )#[], network_controller, universe, p_map, session)
                    """ End Debug """


                    #player.handle_user_input([], network_controller, universe, p_map, session)

                    """ Production """
                    #player.handle_user_input( [], control_center, universe )#[], network_controller, universe, p_map, session)
                    """ End Production """

                else:

                    logn( "map debug", "###", input_controller.get_gameplay_input() )

                    #player.handle_user_input(user_input, network_controller, universe, p_map, session)

                    # Don't react to gameplay input if the network controller has a lock (i.e. waiting for a registered message)
                    if ( not network_controller.is_local_locked() ):

                        # Respond to user gameplay input
                        player.handle_user_input( input_controller.get_gameplay_input(), control_center, universe )#user_input, network_controller, universe, p_map, session)

            else:

                network_controller.lock()

                # It will still have access to network input!
                player.handle_user_input( player.network_input, control_center, universe )#network_controller, universe, p_map, session)

                network_controller.unlock()


        # Validate that we found the local player
        if (local_player):

            # If the local player has died...
            if (local_player.status == STATUS_INACTIVE):

                # Offline logic
                if ( network_controller.get_status() == NET_STATUS_OFFLINE ):

                    # Don't use this logic during dummy sessions (e.g. Gifs)
                    if ( (not ( universe.get_session_variable("core.is-dummy-session").get_value() == "1" )) and
                         (not ( universe.get_session_variable("core.handled-local-death").get_value() == "1" )) ):

                        log2( "Player is dead!" )

                        # Fetch the menu controller;
                        menu_controller = control_center.get_menu_controller()

                        # and the widget dispatcher
                        widget_dispatcher = control_center.get_widget_dispatcher()

                        log2( "menu count:  %s" % menu_controller.count() )
                        if ( True or menu_controller.count() == 0 ):

                            # Fetch active map
                            m = universe.get_active_map()


                            # Puzzle maps death results in a puzzle failed menu appearing, allowing them to restart / leave map / etc.
                            if ( m.get_type() == "puzzle" ):

                                menu_controller.add(
                                    widget_dispatcher.create_puzzle_death_menu()
                                )

                            elif ( m.get_type() == "challenge" ):

                                menu_controller.add(
                                    widget_dispatcher.create_wave_death_menu()
                                )

                                log2( "player has died in challenge room!" )

                            # Linear maps also have their own version of the death menu
                            elif ( m.get_type() == "linear" ):

                                menu_controller.add(
                                    widget_dispatcher.create_linear_death_menu()
                                )

                            # Overworld game over results in a universe-level menu appearing, allowing checking / respawn in town / etc.
                            else:

                                #log2( "Deactivated overworld death menu for debugging..." )
                                #"""
                                menu_controller.add(
                                    widget_dispatcher.create_overworld_death_menu()
                                )
                                #"""

                                log2( "player died in overworld!" )


                        # Remove the local player object to ensure we don't hit this logic again (and thus create a redundant game over menu) before retrying / reloading / whatever...
                        #self.remove_entity_by_type_and_name(GENUS_PLAYER, local_player.name)
                        universe.set_session_variable("core.handled-local-death", "1")


                        # We're done processing now... nothing else matters!  We won't hit this process() call anymore.
                        return


        # Everything that isn't a player will process at a reduced rate during a matrix effect
        if (self.matrix_remaining > 0):

            self.matrix_remaining -= 1


            self.matrix_step += 1

            if (self.matrix_step >= self.matrix_step_max):

                # Reset counter and allow frame processing (pass)
                self.matrix_step = 0

                pass

            else:

                # return to avoid further processing
                return


        # Decrease fright time
        if (self.fright_remaining > 0):
            self.fright_remaining -= 1


        for respawn in self.entities[GENUS_RESPAWN_PLAYER]:

            respawn.process(control_center, universe)#network_controller, universe, p_map, session)


        for enemy in self.entities[GENUS_ENEMY]:

            enemy.process(control_center, universe)#network_controller, universe, p_map, session)
            enemy.handle_ai(control_center, universe)#network_controller, universe, p_map, session)

        for npc in self.entities[GENUS_NPC]:

            npc.process(control_center, universe)#network_controller, universe, p_map, session)
            npc.handle_ai(control_center, universe)#network_controller, universe, p_map, session)

        for bomb in self.entities[GENUS_BOMB]:

            bomb.process(control_center, universe)#network_controller, universe, p_map, session)

        for hologram in self.entities[GENUS_HOLOGRAM]:

            hologram.process(control_center, universe)#network_controller, universe, p_map, session)
            hologram.handle_ai(control_center, universe)#network_controller, universe, p_map, session)

        for gold in self.entities[GENUS_GOLD]:

            gold.process(control_center, universe)#network_controller, universe, p_map, session)


        # Check dig sites
        for y in range( 0, self.traps.get_height() ):
            for x in range( 0, self.traps.get_width() ):

                # Convenience
                trap = self.traps.read(x, y, default_value = None)

                # Validate trap object
                if (trap):

                    # Is this trap active?
                    if ( trap.get_timer() > 0 ):

                        # Lower the timer
                        if ( trap.get_delay() <= 0 ):

                            # Tick, tock
                            trap.increment_timer(-1)


                            # Is it time to refill the tile (for collision detection, etc.)?
                            if ( trap.get_timer() <= 0 ):

                                # Restore tile (for collision detection purposes, etc.)
                                self.tiles.write( x, y, self.tiles_backup.read(x, y) )

                                # Any entity in this tile will be destroyed!
                                r = offset_rect( (x * TILE_WIDTH, y * TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT), self.x, self.y )

                                for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC):

                                    for entity in self.entities[genus]:

                                        if ( intersect(r, entity.get_rect()) ):
                                            entity.queue_death_by_cause(DEATH_BY_TILE_FILL)


                            # No; should we delay the next timer countdown to show the fill pattern effect?
                            elif ( trap.get_timer() <= DIG_FILL_FRAMES ):

                                # This will allow each from of the fill effect to remain visible for a short time...
                                trap.set_delay( DIG_FILL_FRAME_DELAYS[ DIG_FILL_FRAMES - (trap.get_timer() - 0) ] )
                                #print "FRAME: ", self.trap_timers[y][x]


                        else:
                            trap.increment_delay(-1)


    def post_process(self, control_center, universe):#network_controller, universe, p_map, session):

        for enemy in self.entities[GENUS_ENEMY]:
            enemy.post_process(control_center, universe)#network_controller, universe, p_map, session)

        for player in self.entities[GENUS_PLAYER]:
            player.post_process(control_center, universe)#network_controller, universe, p_map, session)

        for npc in self.entities[GENUS_NPC]:
            npc.post_process(control_center, universe)#network_controller, universe, p_map, session)

        for bomb in self.entities[GENUS_BOMB]:
            bomb.post_process(control_center, universe)#network_controller, universe, p_map, session)

        for hologram in self.entities[GENUS_HOLOGRAM]:
            hologram.post_process(control_center, universe)#network_controller, universe, p_map, session)


    def render(self, sx, sy, tilesheet_sprite, additional_sprites, render_sprites_not_tiles = False, gl_color = None, is_editor = False, window_controller = None, max_x = SCREEN_WIDTH, max_y = SCREEN_HEIGHT, scale = 1.0):

        # We'll want to cull sprites that don't appear somewhere within the game's visible region
        visibility_region = window_controller.get_visibility_region()


        # Default to full color, self alpha
        color = (1, 1, 1, self.alpha_controller.get_interval())

        # Check for an explicitly-set color
        if (gl_color):

            # Start with self alpha
            alpha_value = self.alpha_controller.get_interval()

            # If the explicitly-set color contains an alpha, use it as a factor
            if ( len(gl_color) > 3 ):

                # Factor in both the plane's phase alpha and the rendering alpha
                alpha_value *= gl_color[3]

            # Final calculation
            color = (gl_color[0], gl_color[1], gl_color[2], alpha_value)


        # Render level structure
        if (not render_sprites_not_tiles):

            # Determine how many rows to render
            y_render_range = range( 0, int(self.slide_y / TILE_HEIGHT) )

            # If the plane is sliding, we need to do a scissor test...
            if (self.is_sliding):

                r = ( (sx + int(self.dx) + ( (self.x * TILE_WIDTH) + int(self.shift_x) )), (sy + int(self.dy) + ( (self.y * TILE_HEIGHT) + int(self.shift_y) )), int(self.slide_x), int(self.slide_y) )

                # Scissor on the slide region
                window_controller.get_scissor_controller().push(r)


                # We'll want to render one additional row (for the slide-in-progress)
                y_render_range = range( 0, int( (self.slide_y + (TILE_HEIGHT - 1)) / TILE_HEIGHT ) )


            # Base render position (upper-left corner)
            (rx, ry) = (
                sx + int(self.dx) + ( int(scale * self.x * TILE_WIDTH) + int(self.shift_x) ),
                sy + int(self.dy) + ( int(scale * self.y * TILE_HEIGHT) + int(self.shift_y) )
            )

            # Default render width for tile-sized sprites
            (tw, th) = (
                TILE_WIDTH,
                TILE_HEIGHT
            )

            # GL cursor movement per row (line break size, so to speak)
            em = TILE_HEIGHT

            # Adjust for scale if necessary
            if (scale != 1):

                # Scale everything except for the (sx, sy) offset
                (rx, ry) = (
                    sx + int( scale * ( int(self.dx) + ( (self.x * TILE_WIDTH) + int(self.shift_x) ) ) ),
                    sy + int( scale * ( int(self.dy) + ( (self.y * TILE_HEIGHT) + int(self.shift_y) ) ) )
                )

                # Scale default sprite size
                (tw, th) = (
                    int(scale * TILE_WIDTH),
                    int(scale * TILE_HEIGHT)
                )

                # Adjust em to scale
                em = int(scale * TILE_HEIGHT)


            #for y in range( 0, self.tiles.get_height() ):
            for y in y_render_range:

                window_controller.get_gfx_controller().draw_textured_row(rx, ry + (y * em), tilesheet_sprite, self.tiles.get_row_at_index(y), gl_color = color, max_x = max_x, max_y = max_y, scale = scale)


            # Render filling-in tiles as necessary...
            for y in range( 0, self.traps.get_height() ):
                for x in range( 0, self.traps.get_width() ):

                    # Convenience.  Note that we're using read2 to commit an unprotected read, assuming x, y exists in the self.traps DataGrid object.  And it should!
                    #   CAlling the protected read just ruins performance, unfortunately.
                    #trap = self.traps.read(x, y, default_value = None)
                    trap = self.traps.read2(x, y)

                    #"""
                    # Validate Trap object
                    z = trap.get_timer()

                    if ( (z > 0) and (z <= DIG_FILL_FRAMES) ):

                        # Calculate current fill frame
                        frame = DIG_FILL_FRAMES - (trap.get_timer() - 0)

                        # The currently appearing portions of the brick (for this tram timer frame) will fade into view as the trap timer expires...
                        alpha = 1.0 - ((DIG_FILL_FRAME_DELAYS[frame] - trap.get_delay()) / float(DIG_FILL_FRAME_DELAYS[frame]))

                        # Any portions that already faded in during a previous frame should show 100%
                        window_controller.get_gfx_controller().draw_fill_pattern(rx + (x * em), ry + (y * em), self.tiles_backup.read(x, y), tilesheet_sprite, frame, additional_sprites["fill-patterns:history"][ trap.get_fill_pattern() ], gl_color = color)

                        # To create the effect of the current segments fading in, we render the fill mask on top of the tile to finish the process
                        window_controller.get_gfx_controller().draw_sprite(rx + (x * em), ry + (y * em), tw, th, additional_sprites["fill-patterns:mask"][ trap.get_fill_pattern() ], frame = frame, gl_color = set_alpha_for_glcolor(alpha, color))
                    #"""


            # Stop scissor test if we set one during a slide...
            if (self.is_sliding):

                window_controller.get_scissor_controller().pop()

        # Render only sprites
        else:

            # Default rendering point (upper-left corner) for sprites
            (rx, ry) = (
                sx + self.x,
                sy + self.y
            )

            # Scale?
            if (scale != 1):

                # Adjust rendering point accordingly
                (rx, ry) = (
                    sx + int(scale * self.x),
                    sy + int(scale * self.y)
                )

            for genus in self.entities:

                for entity in self.entities[genus]:

                    #if (genus != GENUS_GOLD):
                    if (is_editor):

                        entity.render_scaled(rx, ry, additional_sprites[genus], scale, is_editor, gl_color = color, window_controller = window_controller)

                    else:

                        entity.render(rx, ry, additional_sprites[genus], scale, is_editor, gl_color = color, window_controller = window_controller)

