import traceback
import sys

import math
import random

import time

from conversation import Conversation

from code.controllers.intervalcontroller import IntervalController

from code.game.particle import Particle, Colorcle, Numbercle

from code.utils.common import resize_image

from code.constants.common import *

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.death import *

from code.constants.network import *
from code.constants.newsfeeder import *
#from glfunctions import draw_circle, draw_circle_with_radial_gradient, draw_sprite, draw_rect_frame, draw_rect, draw_rounded_rect, draw_triangle

from code.constants.sound import *

from code.extensions.common import UITemplateLoaderExt

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, logn, intersect, intersect_lengths, offset_rect, wrap_degrees, wrap_rect_for_circumference, arc_between, angle_falls_within_arc, arc_intersection, arc_contains_arc, shorter_arc, xml_encode, xml_decode, set_alpha_for_rgb, parse_rgb_from_string, rgb_to_glcolor, is_numeric



import pygame
from pygame.locals import *

class EntityFrameDatum:

    def __init__(self, sequence, hflip = False, vflip = False):

        # The order of the animation sequence (e.g. (2, 3, 4, 5, 6))
        self.sequence = sequence

        # Flip horizontally / vertically?
        self.hflip = hflip
        self.vflip = vflip


    def get_sequence_length(self):

        return len(self.sequence)


    def get_frame_at_sequence_index(self, index):

        if (index < 0):

            return 0

        elif ( index < len(self.sequence) ):

            return self.sequence[index]

        else:

            return 0


    def get_hflip(self):

        return self.hflip


class EntityAIState:

    def __init__(self, node = None):

        self._compressions_by_attribute_name = {}
        self._attribute_names_by_compression = {}
        # Track whether or not we've compressed hash keys
        self.compressed_keys = False

        # Track the index of each serialized attribute (used in compression)
        self.indices_by_attribute = {}

        # Track translations from index to full (e.g. hex(0) -> ai-behavior)
        self.attributes_by_index = {}


        # AI Behavior
        self.ai_behavior = AI_BEHAVIOR_NORMAL
        self.ai_target = None

        # Which entity (e.g. player1, player2...) is the AI targeting?
        self.ai_target_name = "player1" # default

        # AI mood
        self.ai_mood = AI_MOOD_NORMAL
        self.ai_mood_interval = 0

        # For AI weighting purposes
        self.last_lateral_move = DIR_RIGHT
        self.last_attempted_lateral_move = DIR_RIGHT

        # For vertical alignment purposes (you can only move left/right if you're even with a row)
        self.last_vertical_move = DIR_UP
        self.last_attempted_vertical_move = DIR_UP

        # More AI-specific stuff
        self.ai_frozen = False # Sometimes a bad guy must freeze in place for another bad guy to take the right-of-way
        self.ai_frozen_for = None

        self.ai_freeze_resistance = AI_MAX_FREEZE_RESISTANCE # How long can an enemy avoid being frozen?

        # Enemies that run into one another and for some reason can't take turns
        # will eventually lose their patience and just go the other way.  Usually
        # this happens when looking for a ladder...
        self.ai_patience = AI_MAX_PATIENCE

        # After the AI climbs out of a hole, they won't fall back into the same hole for a short time.
        self.ai_is_trapped = False

        self.ai_trap_time_remaining = 0

        self.ai_trap_exception = None
        self.ai_trap_exception_time = 0

        # Enemies get scared sometimes
        self.ai_fright_remaining = 0


        # Respawn interval
        self.ai_respawn_interval = 0


        # The enemy will flash at the respawn location a few times before actually spawning
        self.ai_flash_interval = 0

        # Is the enemy carrying gold?
        self.ai_is_carrying_gold = False
        self.ai_is_carrying_gold_by_name = ""


        # When the player goes invisible, an enemy will seek the player's last known position
        self.ai_last_known_position = None

        # Territorial entities will stick to a certain territory...
        self.ai_territory = None


    # Helper function that gets attributes
    def save_state_get_attributes(self, compress):

        # Return attributes
        return {
            self.get_key("ai-target-name", compress = compress): self.ai_target_name,
            self.get_key("ai-mood", compress = compress): self.ai_mood,
            self.get_key("ai-mood-interval", compress = compress): self.ai_mood_interval,
            self.get_key("last-lateral-move", compress = compress): self.last_lateral_move,
            self.get_key("last-attempted-lateral-move", compress = compress): self.last_attempted_lateral_move,
            self.get_key("last-vertical-move", compress = compress): self.last_vertical_move,
            self.get_key("last-attempted-vertical-move", compress = compress): self.last_attempted_vertical_move,
            self.get_key("ai-frozen", compress = compress): "%d" % self.ai_frozen,
            self.get_key("ai-frozen-for-name", compress = compress): self.ai_frozen_for.name if (self.ai_frozen_for != None) else "", # Sorry
            self.get_key("ai-freeze-resistance", compress = compress): self.ai_freeze_resistance,
            self.get_key("ai-patience", compress = compress): self.ai_patience,
            self.get_key("ai-is-trapped", compress = compress): "%d" % self.ai_is_trapped,
            self.get_key("ai-trap-time-remaining", compress = compress): self.ai_trap_time_remaining,
            self.get_key("ai-trap-exception-x", compress = compress): self.ai_trap_exception[0] if (self.ai_trap_exception != None) else -1, # Very sorry
            self.get_key("ai-trap-exception-y", compress = compress): self.ai_trap_exception[1] if (self.ai_trap_exception != None) else -1, # I mean it
            self.get_key("ai-trap-exception-time", compress = compress): self.ai_trap_exception_time,
            self.get_key("ai-fright-remaining", compress = compress): self.ai_fright_remaining,
            self.get_key("ai-respawn-interval", compress = compress): self.ai_respawn_interval,
            self.get_key("ai-flash-interval", compress = compress): self.ai_flash_interval,
            self.get_key("ai-is-carrying-gold", compress = compress): "%d" % self.ai_is_carrying_gold,
            self.get_key("ai-is-carrying-gold-by-name", compress = compress): self.ai_is_carrying_gold_by_name
        }


    # Calculate compressed attribute strings
    def compress_keys(self, keys):

        # Sort keys alphabetically
        keys.sort()

        # Loop through keys, converting each key to a hex string
        for i in range( 0, len(keys) ):

            # Convert to hex string (e.g. 0: 0x0, 1: 0x1, etc.)
            self.indices_by_attribute[ keys[i] ] = i#hex(i)

            # Save reverse lookup as well
            #self.attributes_by_compressed_key[ hex(i) ] = keys[i]
            self.attributes_by_index[i] = keys[i]


    def configure(self, options):

        if ( "ai-behavior" in options ):
            self.ai_behavior = int( options["ai-behavior"] )


        # For chaining
        return self


    # Get key
    def get_key(self, key, compress = False, decompress = False):

        # Get compressed version?
        if (compress):

            # Return
            return self.compressed_keys_by_attribute[key]

        # Get decompressed version?
        elif (decompress):

            # Return
            return self.attributes_by_compressed_key[key]

        # Return plain text
        else:
            return key


    # AI entities can save/load current AI data
    def save_state(self, compress = False):

        # Scope
        attributes = {}

        # Create node
        node = XMLNode("ai-state")


        # Will we compress the keys (less bandwidth in cooperative mode)?
        if (compress):

            # Do we need to initialize compression key translations?
            if (not self.compressed_keys):

                # Generate default attributes without compression.
                # We need to know the keys for compression.
                attributes = self.save_state_get_attributes(compress = False)

                # Compress using the known keys
                self.compress_keys( attributes.keys() )

                # Set flag
                self.compressed_keys = True


            # Calculate attributes without compression
            attributes = self.save_state_get_attributes(compress = False)

            # Prepare inner text
            s = ""

            # Loop through index values
            for i in range( 0, len(self.indices_by_attribute) ):

                # Add to innerXml string with trailing comma
                s += "%s," % attributes[ self.attributes_by_index[i] ]

            # Set inner text (strip trailing comma)
            node.set_inner_text(
                s.strip(",")
            )


        # No compression; set attributes
        else:

            # Calculate attributes
            attributes = self.save_state_get_attributes(compress = compress)

            # Set node attributes
            node.set_attributes(attributes)


        # Return node
        return node


    # Requires a given Map object to fetch entity frozen for (hack, lame)
    def load_state(self, node, m, compress = False):

        # Will we use compressed keys (less bandwidth in cooperative mode)?
        if (compress):

            # Do we need to initialize compression key translations?
            if (not self.compressed_keys):

                # Generate default attributes without compression.
                # We need to know the keys for compression.
                attributes = self.save_state_get_attributes(compress = False)

                # Do it now
                self.compress_keys( attributes.keys() )

                # Set flag
                self.compressed_keys = True


            # Calculate attributes without compression
            attributes = self.save_state_get_attributes(compress = False)

            # Get inner text
            s = node.get_inner_text()
            values = s.split(",")

            # Loop through index values and implicitly add attributes to the received node
            for i in range( 0, len(values) ):

                # Set appropriate attribute
                node.set_attribute( self.attributes_by_index[i], values[i] )

            """ Now, when we move into the ai_property = node.get_attribute("ai-property") code,
                we will find the attributes in the node. """


        self.ai_target_name = node.get_attribute("ai-target-name")

        self.ai_mood = int( node.get_attribute("ai-mood") )
        self.ai_mood_interval = int( node.get_attribute("ai-mood-interval") )

        self.last_lateral_move = int( node.get_attribute("last-lateral-move") )
        self.last_attempted_lateral_move = int( node.get_attribute("last-attempted-lateral-move") )

        self.last_vertical_move = int( node.get_attribute("last-vertical-move") )
        self.last_attempted_vertical_move = int( node.get_attribute("last-attempted-vertical-move") )

        self.ai_frozen = (int( node.get_attribute("ai-frozen") ) == 1)
        self.ai_frozen_for = m.get_entity_by_name( node.get_attribute("ai-frozen-for-name") )

        self.ai_freeze_resistance = int( node.get_attribute("ai-freeze-resistance") )

        self.ai_patience = int( node.get_attribute("ai-patience") )

        self.ai_is_trapped = (int( node.get_attribute("ai-is-trapped") ) == 1)

        self.ai_trap_time_remaining = int( node.get_attribute("ai-trap-time-remaining") )

        self.ai_trap_exception = (
            int( node.get_attribute("ai-trap-exception-x") ),
            int( node.get_attribute("ai-trap-exception-y") )
        )

        self.ai_trap_exception_time = int( node.get_attribute("ai-trap-exception-time") )

        # Enemies get scared sometimes
        self.ai_fright_remaining = int( node.get_attribute("ai-fright-remaining") )

        self.ai_respawn_interval = int( node.get_attribute("ai-respawn-interval") )
        self.ai_flash_interval = int( node.get_attribute("ai-flash-interval") )

        self.ai_is_carrying_gold = ( int( node.get_attribute("ai-is-carrying-gold") ) == 1 )
        self.ai_is_carrying_gold_by_name = "%s" % node.get_attribute("ai-is-carrying-gold-by-name")


class Entity:

    def __init__(self):

        self.genus = None
        self.species = None

        self.name = ""

        # Optional entity class.  Useful for querying total number of merchants, etc.
        self.class_name = ""

        self.nick = ""
        self.title = ""

        # Some entities only render in level editing mode
        self.editor_only = False


        # An entity may conceivably alter the original surface (e.g. colored players in a multiplayer game),
        # requiring the entity itself to have its own working texture area
        self.working_texture = None

        # Player entities can have custom primary colors.  I'll use this variable to track any given entity's primary color.
        self.primary_color = (255, 255, 255)


        # Processing status
        self.status = STATUS_ACTIVE

        # During netplay, some entities may enter a "pending" sync state where other entities ignore them (i.e. other players)
        self.sync_status = SYNC_STATUS_READY


        # We can choose to lock entities.  This is uncommon, and each object may handle locking in its own unique way.
        # During netplay, clients will "lock" a bomb until the server confirms it has received notice (to share with other players)
        self.lock_count = 0


        # We can queue an enemy to die during post-processing
        self.queued_death_by_cause = None

        # We can also queue a gold drop at a tile location
        self.queued_gold_drop_location = None


        # The network may dictate certain input commands (e.g. motion control)
        self.network_input = []

        # Ghost entities (e.g. holograms) won't be factored into memory saves
        self.is_ghost = False

        # Will this entity corpse upon death?
        self.is_disposable = False

        # Trackers
        self.alive = True
        self.corpsed = False

        # An entity (at present, only a Player entity) might be using a shield (personal shield skill)
        self.has_shield = False

        self.x = 0.0
        self.y = 0.0

        self.direction = DIR_RIGHT


        # Did the entity move during this frame?
        self.moved_this_frame = False


        # Which entity types can this entity collide with during movement?
        self.colliding_entity_types_during_movement = (GENUS_PLAYER, GENUS_ENEMY)

        # Which entity types can it collide with during gravity?
        self.colliding_entity_types_during_gravity = (GENUS_PLAYER, GENUS_ENEMY)


        # What input might the entity have received in the previous frame?
        self.previous_input = []

        self.frame = 0

        self.frame_interval = 0
        self.frame_delay = 5

        # Define this in inheriting classes
        self.frame_indices = {}


        # Base entity speed
        self.speed = 2.25
        self.base_speed = self.speed

        # Remember default speed in case we want to revert at any point
        self.default_speed = self.speed


        # During netplay, we'll apply subtle modifications to an out-of-sync entity's speed, subtly
        # moving it closer to the desired location without resorting to teleportation.
        self.network_latency_dx = 0
        self.network_latency_dy = 0

        # Each entity can also define the rate at which it will try to correct for network latency.
        self.network_latency_correction_rate = 0.5


        # If we're going to use a "footstep" sound effect for this entity, we'll only add it every so often
        self.footstep_interval = FOOTSTEP_INTERVAL_MAX


        # Sometimes entities (NPCs, mostly) will have a "patrol delay" between hotspots (they'll just stand around for a moment)
        self.patrol_delay = 0


        # An entity might be able to sprint; we'll append that to their movement speed when applicable...
        self.sprint_bonus = 0.0


        # Yes, I'm just hard-coding these.  Whatever...
        self.width = 24
        self.height = 24


        self.can_move = False
        self.knows_how_to_hang = True # Can this entity hang onto monkey bars and ladders?  (bombs, for instance, cannot...)


        # Sometimes (e.g. during a dig attempt), an entity will endure a brief move delay...
        self.move_delay = 0

        # Well ok, I'm going to put the dig delay in its own variable, so that's a bad example...
        self.dig_delay = 0

        # The player can do multi-tile digs (with jackhammer / earth-mover skills); we'll queue the additional digs...
        self.queued_digs = []


        # We may need to store a reference to one or more bombs for the remote-bomb skill (the second skill activation detonates the bomb(s))
        self.remote_bombs = []


        # Determine how to react to collisions...
        self.food_chain_position = 0


        # An entity can be invincible (chiefly used by bombs with bomb shield)
        self.invincible = False

        # An entity may, alternately, have damage resistance...
        self.damage_resistance = 0


        # A script can tell an entity to move to a certain location
        self.scripted_target = None

        # A script can also instruct an entity to pause for a brief while
        self.pause_time = 0


        # We'll configure this in Entity.describe
        self.ai_state = EntityAIState()


        # Hotspot tracking
        self.hotspots = []
        self.current_hotspot = 0





        # Is the player climbing?  (We'll ignore gravity if so.)
        self.is_climbing = False

        # How high/low will the current ladder go?
        self.climb_ceiling = 0
        self.climb_floor   = 0

        # Can you drop off of the bottom rung of the ladder?
        self.climb_droppable = False


        # Is the player swinging on a monkey bar?  (We'll ignore gravity if so.)
        self.is_swinging = False

        # Track the monkey bar's range
        self.swing_start = 0
        self.swing_end = 0


        # Explode upon death
        self.particles = []

        # Sound effect necessary?
        self.sfx_queue = []


    def describe(self, options):

        if ( "x" in options ):
            self.x = float( int( options["x"] ) * TILE_WIDTH )

        if ( "y" in options ):
            self.y = float( int( options["y"] ) * TILE_HEIGHT )

        if ( "absolute-x" in options ):
            self.x = float( options["absolute-x"] )

        if ( "absolute-y" in options ):
            self.y = float( options["absolute-y"] )

        if ( "name" in options ):
            self.name = options["name"]

        if ( "class" in options ):
            self.class_name = options["class"]

        if ( "nick" in options ):
            self.nick = options["nick"]

        if ( "title" in options ):
            self.title = options["title"]

        if ( "genus" in options ):
            self.genus = int( options["genus"] )


        # Configure base AI state
        self.ai_state = EntityAIState().configure(
            options
        )


        # For chaining
        return self


    def customize(self, options):

        # For chaining
        return self


    def compile_xml_string(self, prefix = ""):

        # Create node
        node = XMLNode("entity")

        # Set properties
        node.set_attributes({
            "name": xml_encode( "%s" % self.name ),
            "class": xml_encode( "%s" % self.class_name ),
            "nick": xml_encode( "%s" % self.nick ),
            "title": xml_encode( "%s" % self.title ),
            "x": xml_encode( "%d" % int( self.get_x() / TILE_WIDTH ) ),
            "y": xml_encode( "%d" % int( self.get_y() / TILE_HEIGHT ) ),
            "genus": xml_encode( "%d" % self.genus ),
            "ai-behavior": xml_encode( "%d" % self.ai_state.ai_behavior )
        })

        # Return xml...
        return node.compile_xml_string()
        #xml += "x = '%d' y = '%d' genus = '%d' ai-behavior = '%d' name = '%s' class = '%s' nick = '%s' title = '%s' />\n" %
        #, self.ai_state.ai_behavior, self.name.replace("'", "&apos;"), xml_encode(self.class_name), self.nick.replace("'", "&apos;"), self.title.replace("'", "&apos;"))
        #return xml

    # Some inheriting classes will overwrite this with additional data
    def save_state(self):

        # Create node
        node = XMLNode("entity")

        # Set properties
        node.set_attributes({
            "name": xml_encode( "%s" % self.name ),
            "class": xml_encode( "%s" % self.class_name ),
            "status": xml_encode( "%d" % self.status ),
            "alive": xml_encode( "%d" % self.alive ),
            "corpsed": xml_encode( "%s" % self.corpsed )
        })
        #xml = "%s<entity name = '%s' class = '%s' status = '%d' alive = '%d' corpsed = '%s' />\n" % (prefix, self.name, xml_encode(self.class_name), self.status, self.alive, self.corpsed)

        # Return node
        return node


    # Save AI state data
    def save_ai_state(self, compress = False):

        # Save base state data first
        root = self.save_state()

        # Add in position data for AI state
        root.set_attributes({
            "x": xml_encode( "%d" % self.get_x() ),
            "y": xml_encode( "%d" % self.get_y() ),
            "direction": xml_encode( "%d" % self.get_direction() )
        })

        # Now add in AI state data as a child node
        root.add_node(
            self.ai_state.save_state(compress = compress)
        )

        # Return modified root node
        return root


    # Same deal here; some will overwrite the recall function...
    def load_state(self, node):

        # Recall class name
        if ( node.has_attribute("class") ):
            self.class_name = xml_decode( node.get_attribute("class") )

        if ( node.has_attribute("status") ):
            self.status = int( node.attributes["status"] )

        if ( node.has_attribute("corpsed") ):
            self.corpsed = (node.attributes["corpsed"] == "True")

        if ( node.has_attribute("alive") ):
            self.alive = ( int( node.get_attribute("alive") ) == 1 )


        # Inactivate entities that are not corpsed should "die" so that they respawn...
        if ( (self.status == STATUS_INACTIVE) and (not self.corpsed) ):

            self.respawn()


    # Load AI state.
    # Requires a Map object for some reason, enemy frozen for calculation...
    def load_ai_state(self, node, m, compress = False):

        # Load base state data first
        self.load_state(node)

        # NOw, load AI state data from the child node
        self.ai_state.load_state(
            node.find_node_by_tag("ai-state"), m, compress = compress
        )


    # Validate AI "trapped" state.  Ensures that a "trapped" enemy is actually
    # in a trap and not at the spawn location.
    def validate_ai_trapped_state(self, m):

        # Known to be trapped?
        if (self.ai_state.ai_is_trapped):

            # If the map does not have an available trap there,
            # then reset trap status.
            if ( not m.trap_exists_at_tile_coords( int(self.get_x() / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT), self.ai_state.ai_trap_exception ) ):

                # Not trapped
                self.ai_state.ai_is_trapped = False
                self.ai_state.ai_trap_time_remaining = 0

                # No exception
                self.ai_state.ai_trap_exception = None
                self.ai_state.ai_trap_exception_time = 0

                return False

            return True

        else:
            return False


    # Sync AI state.
    def sync_ai_state(self, node):

        # Get true location
        (x, y) = (
            int( node.get_attribute("x") ),
            int( node.get_attribute("y") )
        )

        # Update entity direction always
        self.set_direction( int( node.get_attribute("direction") ) )

        """
        # If both x and y are incorrect, then we will teleport-update the entity
        if ( (self.get_x() != x) and (self.get_y() != y) ):

            # Teleport
            self.set_x(x)
            self.set_y(y)

            # No latency at this moment
            self.network_latency_dx = 0
            self.network_latency_dy = 0
        """

        # Is everything right?
        if ( (x == self.get_x()) and (y == self.get_y()) ):

            # No latency on either axis
            self.network_latency_dx = 0
            self.network_latency_dy = 0

        # If only x is wrong, then let's try modifying this entity's speed slightly
        elif ( (self.get_x() != x) and (y == self.get_y()) ):

            # No y-axis latency
            self.network_latency_dy = 0


            # Calculate x-axis delta
            dx = abs( x - self.get_x() )

            # When the enemy grossly falls out of sync, we'll teleport...
            if ( dx >= TILE_WIDTH ):

                # Teleport
                self.set_x(x)

                # No x-axis latency after teleport
                self.network_latency_dx = 0

            # Otherwise, let's try smoothing out the difference
            else:

                # Note x-axis latency
                self.network_latency_dx = ( self.get_x() - x )

        # If only y is wrong, then let's try modifying this entity's speed slightly
        elif ( (self.get_y() != y) and (x == self.get_x()) ):

            # No x-axis latency
            self.network_latency_dx = 0


            # Calculate y-axis delta
            dy = abs( y - self.get_y() )

            # When the enemy grossly falls out of sync, we'll teleport...
            if ( dy >= TILE_HEIGHT ):

                # Teleport
                self.set_y(y)

                # No x-axis latency after teleport
                self.network_latency_dy = 0

            # Otherwise, let's try smoothing out the difference
            else:

                # Note y-axis latency
                self.network_latency_dy = ( self.get_y() - y )

        # If both axes are wrong, then we will apply smoothing
        # to both axes!
        else:

            # Calculate x-axis delta
            dx = abs( x - self.get_x() )

            # When the enemy grossly falls out of sync, we'll teleport...
            if ( dx >= TILE_WIDTH ):

                # Teleport
                self.set_x(x)

                # No x-axis latency after teleport
                self.network_latency_dx = 0

            # Otherwise, let's try smoothing out the difference
            else:

                # Note x-axis latency
                self.network_latency_dx = ( self.get_x() - x )


            # Calculate y-axis delta
            dy = abs( y - self.get_y() )

            # When the enemy grossly falls out of sync, we'll teleport...
            if ( dy >= TILE_HEIGHT ):

                # Teleport
                self.set_y(y)

                # No x-axis latency after teleport
                self.network_latency_dy = 0

            # Otherwise, let's try smoothing out the difference
            else:

                # Note y-axis latency
                self.network_latency_dy = ( self.get_y() - y )

        """
        else:

            # No latency on either axis
            self.network_latency_dx = 0
            self.network_latency_dy = 0
        """


    def get_debug_circle(self):

        (x1, y1) = (
            math.cos( math.radians(self.degrees) ) * (self.radius - (self.height / 2)),
            math.sin( math.radians(self.degrees) ) * (self.radius - (self.height / 2))
        )

        return (x1, y1)
        window_controller.get_geometry_controller().draw_circle(320 + x1, 240 + y1, (self.width / 2), None, (0, 0, 255))


    # Set entity name
    def set_name(self, name):

        # Update name
        self.name = name


    # Get entity name
    def get_name(self):

        # Return
        return self.name


    # Set class name
    def set_class(self, class_name):

        # Update
        self.class_name = class_name


    # Get class
    def get_class(self):

        # Return
        return self.class_name


    # See if this NPC has a given class name
    def has_class(self, class_name):

        result = any( o == class_name for o in self.class_name.split(" ") )
        logn( "entity debug", "npc '%s' has class '%s' within '%s?' ... %s" % (self.name, class_name, self.class_name, result) )

        # Check all classes given to this entity
        return any( o == class_name for o in self.class_name.split(" ") )


    # Colorify with semicolon-separated values (if/a)
    def colorify(self, ssv):
        return


    def queue_sound(self, sfx_key):
        self.sfx_queue.append(sfx_key)

    def get_status(self):

        return self.status

    def set_status(self, status):

        self.status = status

    def get_sync_status(self):

        #return self.sync_status
        return SYNC_STATUS_READY

    def set_sync_status(self, status):

        self.sync_status = status


    # Check lock status
    def is_locked(self):

        # Simple check
        return (self.lock_count > 0)


    # Lock entity
    def lock(self):

        # Increment
        self.lock_count += 1


    # Unlock entity
    def unlock(self):

        # Decrement
        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            # Clamp
            self.lock_count = 0


    def is_touchable(self):

        #return ( (self.sync_status == SYNC_STATUS_READY) and (self.status == STATUS_ACTIVE) and (self.alive) )
        return ( (self.status == STATUS_ACTIVE) and (self.alive) )

    def get_x(self):

        if (self.x >= 0):
            return int(self.x + 0.001)

        else:
            return int(self.x - 0.001)

    def get_y(self):

        if (self.y >= 0):
            return int(self.y + 0.001)

        else:
            return int(self.y - 0.001)

    def set_x(self, x):

        self.x = x

    def set_y(self, y):

        self.y = y

    def set_xy(self, x, y, p_map = None):

        self.x = x
        self.y = y

    # Get bounding box
    def get_rect(self):

        return ( self.get_x(), self.get_y(), self.width, self.height )


    # Get bounding box, with scale factored in (mostly for editor)
    def get_scaled_rect(self, scale = 1.0):

        (tx, ty) = (
            int( self.get_x() / TILE_WIDTH ),
            int( self.get_y() / TILE_HEIGHT )
        )

        (remainderX, remainderY) = (
            0,#self.get_x() % TILE_WIDTH,
            0#self.get_y() % TILE_HEIGHT
        )

        return (
            int( (tx * int(scale * TILE_WIDTH)) + (scale * remainderX) ),
            int( (ty * int(scale * TILE_HEIGHT)) + (scale * remainderY) ),
            int( scale * self.width ),
            int( scale * self.height )
        )
        return (
            int( scale * self.get_x() ),
            int( scale * self.get_y() ),
            int( scale * self.width ),
            int( scale * self.height )
        )


    def get_left_border(self):
        return ( self.get_x(), self.get_y(), 1, self.height )

    def get_right_border(self):
        return ( self.get_x() + (self.width - 1), self.get_y(), 1, self.height )

    def position_at_waypoint(self, trigger):

        (x, y) = (
            trigger.x * TILE_WIDTH,
            trigger.y * TILE_HEIGHT
        )

        self.x = x
        self.y = y

    def intersects_entity(self, entity, max_y = "unused"):

        # You can't intersect with a dead entity
        if (not entity.alive):
            return False

        else:

            rA = self.get_rect()
            rB = entity.get_rect()

            return ( intersect(rA, rB) )


    # Get an entity's base speed.  Overwrite as necessary to account for player's equipped inventory...
    def get_speed(self):

        return self.speed


    # Get entity's base speed, without factoring in inventory bonsues.
    def get_base_speed(self):

        # Return base speed value
        return self.base_speed


    # Get an entity's default base speed
    def get_default_speed(self):

        return self.default_speed


    # Set an entity's base speed.
    def set_speed(self, speed):

        # Update
        self.speed = speed


    # Adjust this entity's speed, returning a separate value for each axis.
    # We adjust the given values for known latency.
    def adjust_speed_for_latency(self, speed_x, speed_y, target_x, target_y):

        # x-axis latency adjustment; should we be farther to the right?
        if (self.network_latency_dx < 0):

            # If the enemy is going to move to the left, then we should slow him down (he's too far left already)
            if ( target_x < self.get_x() ):

                # Slow down
                z = speed_x
                speed_x += max(-self.network_latency_correction_rate, self.network_latency_dx)
                logn( "latency-correction", "adjusted speed_x (x-axis, too far left, moving left slowly):  %s -> %s" % (z, speed_x) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dx += self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dx > 0):

                    # Clamp
                    self.network_latency_dx = 0

            # If the enemy is going to move to the right, then he's behind schedule and we'll speed him up
            else:

                # Speed up
                z = speed_x
                speed_x -= max(-self.network_latency_correction_rate, self.network_latency_dx)
                logn( "latency-correction", "adjusted speed_x (x-axis, too far left, moving right quickly):  %s -> %s" % (z, speed_x) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dx += self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dx > 0):

                    # Clamp
                    self.network_latency_dx = 0

        # Is this enemy too far to the right, out of sync?
        elif (self.network_latency_dx > 0):

            # If the enemy is going to move to the left, then we should speed him up (he's too far to the right currently)
            if ( target_x < self.get_x() ):

                # Speed up
                z = speed_x
                speed_x += min(self.network_latency_correction_rate, self.network_latency_dx)
                logn( "latency-correction", "adjusted speed_x (x-axis, too far right, moving left quickly):  %s -> %s" % (z, speed_x) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dx -= self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dx < 0):

                    # Clamp
                    self.network_latency_dx = 0

            # If the enemy is going to move to the right, then he's ahead of schedule and we'll slow him down
            else:

                # Slow down
                z = speed_x
                speed_x -= min(self.network_latency_correction_rate, self.network_latency_dx)
                logn( "latency-correction", "adjusted speed_x (x-axis, too far right, moving right slowly):  %s -> %s" % (z, speed_x) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dx -= self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dx < 0):

                    # Clamp
                    self.network_latency_dx = 0


        # y-axis latency adjustment; should we be farther down?
        if (self.network_latency_dy < 0):

            # If the enemy is going to move to the left, then we should slow him down (he's too far left already)
            if ( target_y < self.get_y() ):

                # Slow down
                speed_y += max(-self.network_latency_correction_rate, self.network_latency_dy)
                log2( "Latency Correction (y-axis):  %s" % max(-self.network_latency_correction_rate, self.network_latency_dy) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dy += self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dy > 0):

                    # Clamp
                    self.network_latency_dy = 0

            # If the enemy is going to move to the right, then he's behind schedule and we'll speed him up
            else:

                # Speed up
                speed_y -= max(-self.network_latency_correction_rate, self.network_latency_dy)
                log2( "Latency Correction (y-axis):  %s" % max(-self.network_latency_correction_rate, self.network_latency_dy) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dy += self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dy > 0):

                    # Clamp
                    self.network_latency_dy = 0

        # Is this enemy too far down, out of sync?
        elif (self.network_latency_dy > 0):

            # If the enemy is going to move to the left, then we should speed him up (he's too far to the right currently)
            if ( target_y < self.get_y() ):

                # Speed up
                speed_y += min(self.network_latency_correction_rate, self.network_latency_dy)
                log2( "Latency Correction (y-axis):  %s" % min(self.network_latency_correction_rate, self.network_latency_dy) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dy -= self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dy < 0):

                    # Clamp
                    self.network_latency_dy = 0

            # If the enemy is going to move to the right, then he's behind schedule and we'll speed him up
            else:

                # Slow down
                speed_y -= min(self.network_latency_correction_rate, self.network_latency_dy)
                log2( "Latency Correction (y-axis):  %s" % min(self.network_latency_correction_rate, self.network_latency_dy) )


                # Reduce the offset (this is assuming the seek_location move call succeeds)
                self.network_latency_dy -= self.network_latency_correction_rate

                # Don't overshoot 0
                if (self.network_latency_dy < 0):

                    # Clamp
                    self.network_latency_dy = 0

        # Return adjusted values
        return (speed_x, speed_y)


    def ai_can_freeze(self, p_map, caller):

        # Only an enemy entity can be frozen
        if (self.genus == GENUS_ENEMY):

            if (self.ai_state.ai_freeze_resistance > 0):
                self.ai_state.ai_freeze_resistance -= 2

                return False

            else:

                # Special case here.  If the entity we're trying to freeze
                # is already colliding with another entity (which would have
                # to be the 3rd-party entity it previously froze), then
                # we're not going to allow it.  We can't have the enemies
                # walking all over one another...
                for entity in p_map.master_plane.query_interentity_collision_for_entity(self).get_results():

                    # If we're intersecting with a 3rd-party entity, then let's say we can't freeze right now
                    if (entity != caller):

                        # Maybe later
                        return False


                # Looks like we're free!
                return True

        # Only enemies can be frozen
        else:

            # Verboten!
            return False


    def handle_entity_touch(self, entity, control_center, universe):
        #print "%s touched you, %s!" % (entity.name, self.name)

        #f = open( os.path.join("debug", "debug.ai.txt"), "a" )
        #f.write("%s touched %s\n" % (entity.name, self.name))
        #f.close()
        return


    # Add a hotspot (trigger name) to this entity's pathfinding hotspots
    def add_hotspot(self, name):

        # Add hotspot
        self.hotspots.append(name)

        # Done
        return True


    # Clear all hotspots, perhaps to recreate a new list of hotspots.
    # I'm not sure I ever use this, to be honest.
    def clear_hotspots(self):

        # Clear!
        self.hotspots = []

        # Reset index
        self.current_hotspot = 0

        # Done
        return True


    # Set an entity's preferred target, by player index.
    # Typically used for cooperative maps, where we want some enemy to target some certain player.
    def set_preferred_target_by_index(self, index, control_center, universe):

        # Counter to track active player slot.
        slot = 0

        # Loop through online players
        for i in range(1, 5):

            # Has player in this slot joined?
            if (
                int( universe.get_session_variable("net.player%d.joined" % i).get_value() ) == 1
            ):

                # Increment slot counter
                slot += 1

                # Is this the player we prefer to target?
                if (slot == index):

                    # Track by name
                    self.preferred_target_name = "player%d" % slot

                    # Successfully targeted
                    return True


        # Not successfully targeted (player not available?)
        return False


    # Set an entity's current target, by target player name.
    # If the given player name represents a new target, we'll
    # immediately sync the enemy AI data to all clients.
    def set_current_target_name(self, name, control_center, universe):

        # Offline logic:  Set name and return
        if ( control_center.get_network_controller().get_status() == NET_STATUS_OFFLINE ):

            # Set and forget
            self.current_target_name = name

            # Update our record of the player target's name
            self.ai_state.ai_target_name = name

        # Server logic:  ignore duplicates, sync enemy AI on change
        elif ( control_center.get_network_controller().get_status() == NET_STATUS_SERVER ):

            # Don't process duplicates
            if (name != self.last_known_target_name):

                # Set current target name
                self.current_target_name = name

                # Update last known target name
                self.last_known_target_name = name

                # Set flag to request an immediate AI update on all enemies.
                self.requires_ai_update = True

                # Update our record of the player target's name
                self.ai_state.ai_target_name = name

        # Client logic:  Set name and return
        elif ( control_center.get_network_controller().get_status() == NET_STATUS_CLIENT ):

            # Set and forget
            self.current_target_name = name

            # Update our record of the player target's name
            self.ai_state.ai_target_name = name


    def handle_message(self, message, target, param, control_center, universe):

        # Add a new hotspot for this entity
        if (message == "add-hotspot"):

            targets = "%s;%s" % (target, param)
            targets = targets.split(";")

            for t in targets:

                if (t.strip() != ""):
                    self.hotspots.append( t.strip() )

            return True

        # Clear all hotspots (likely to make room for new ones)
        elif (message == "clear-hotspots"):

            self.hotspots = []

            # Reset hotspot index
            self.current_hotspot = 0

            return True

        elif (message == "start-motion"):

            # Fetch active map
            m = universe.get_active_map()

            pieces = param.split(";")

            (x, y, direction) = (
                int( pieces[0] ),
                int( pieces[1] ),
                int( pieces[2] )
            )

            self.set_xy(x, y, m)

            if (direction == DIR_LEFT):

                for other_direction in (INPUT_MOVE_RIGHT, INPUT_MOVE_UP, INPUT_MOVE_DOWN):

                    if (other_direction in self.network_input):

                        self.network_input.remove(other_direction)

                if ( not (INPUT_MOVE_LEFT in self.network_input) ):

                    self.network_input.append(INPUT_MOVE_LEFT)

            elif (direction == DIR_RIGHT):

                for other_direction in (INPUT_MOVE_LEFT, INPUT_MOVE_UP, INPUT_MOVE_DOWN):

                    if (other_direction in self.network_input):

                        self.network_input.remove(other_direction)

                if ( not (INPUT_MOVE_RIGHT in self.network_input) ):

                    self.network_input.append(INPUT_MOVE_RIGHT)

            elif (direction == DIR_UP):

                for other_direction in (INPUT_MOVE_LEFT, INPUT_MOVE_RIGHT, INPUT_MOVE_DOWN):

                    if (other_direction in self.network_input):

                        self.network_input.remove(other_direction)

                if ( not (INPUT_MOVE_UP in self.network_input) ):

                    self.network_input.append(INPUT_MOVE_UP)

            elif (direction == DIR_DOWN):

                for other_direction in (INPUT_MOVE_LEFT, INPUT_MOVE_RIGHT, INPUT_MOVE_UP):

                    if (other_direction in self.network_input):

                        self.network_input.remove(other_direction)

                if ( not (INPUT_MOVE_DOWN in self.network_input) ):

                    self.network_input.append(INPUT_MOVE_DOWN)


        elif (message == "stop-motion"):

            # Fetch active map
            m = universe.get_active_map()

            (x, y) = param.split(";")

            self.set_xy( int(x), int(y), m )

            for direction in (INPUT_MOVE_LEFT, INPUT_MOVE_RIGHT, INPUT_MOVE_UP, INPUT_MOVE_DOWN):

                if (direction in self.network_input):

                    self.network_input.remove(direction)


        elif (message == "net.client-request.dig"):

            # Fetch active map
            m = universe.get_active_map()

            (x, y, tx, ty) = (
                int( pieces[0] ),
                int( pieces[1] ),
                int( pieces[2] ),
                int( pieces[3] )
            )

            # Is it ok to put the client at that location?  Nothing in the way?
            if ( m.master_plane.count_enemies_in_rect( (x, y, self.width, self.height), exceptions = [self] ) == 0 ):

                result = m.dig_tile_at_tile_coords(tx, ty)

                if (result == DIG_RESULT_SUCCESS):

                    pass

                else:

                    pass


        elif (message == "net.dig"):

            # Fetch active map
            m = universe.get_active_map()

            pieces = param.split(";")

            (x, y, direction, tx, ty) = (
                int( pieces[0] ),
                int( pieces[1] ),
                int( pieces[2] ),
                int( pieces[3] ),
                int( pieces[4] )
            )

            # Quickly emulate a call to "stop-motion"
            self.handle_message("stop-motion", target, "%d;%d" % (x, y), control_center, universe)

            # Dig the given tile
            m.dig_tile_at_tile_coords(tx, ty)

        # Set warehouses for an NPC
        elif (message == "set-warehouses"):

            # Reset warehouses
            self.warehouses = []

            # Check params
            csv = "%s" % param
            warehouses = csv.split(";")

            # Populate
            for w in warehouses:

                if (w.strip() != ""):
                    self.warehouses.append( w.strip() )

            return True


        # Clear vendor inventory
        elif (message == "clear-vendor-inventory"):

            # Clear
            self.clear_vendor_inventory()

            # All done
            return True


        # Add an item to a vendor's inventory
        elif (message == "add-to-vendor-inventory"):

            # Read the param to get the item name
            item_name = param

            # Attempt to update inventory
            self.add_item_to_vendor_inventory(item_name, universe)

            # All done
            return True


        elif (message == "change-ai"):

            # Convert from a raw string (param)
            self.ai_state.ai_behavior = AI_BEHAVIOR_TRANSLATIONS[param]

            return True


        elif (message == "seek-target"):

            # Fetch active map
            m = universe.get_active_map()

            t = m.get_trigger_by_name(target)

            (x, y) = (
                t.x * TILE_WIDTH,
                t.y * TILE_HEIGHT
            )

            #print "'%s' going to seek..." % self.name

            # This is to make sure we flag can_move properly...
            self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = False)


            speed = self.get_speed(universe)

            self.seek_location(x, y, vx = speed, vy = speed, universe = universe)

            # Finished seeking?
            return ( (self.get_x() == x) and (self.get_y() == y) )

        elif (message == "zap-target"):

            # Fetch active map
            m = universe.get_active_map()

            # Get the trigger by name
            t = m.get_trigger_by_name(target)

            # Validate
            if (t):

                # Position the entity at the given waypoint trigger
                self.position_at_waypoint(t)

            return True

        elif (message == "pause"):

            self.pause_time += 1

            if (self.pause_time >= int(param)):

                self.pause_time = 0

                return True

            else:

                return False

        elif (message == "set-passcode"):

            if (self.genus == GENUS_NPC):

                if (self.species == "terminal"):

                    self.passcode = param
                    self.locked = True

            return True

        elif (message == "unlock"):

            if (self.genus == GENUS_NPC):

                if (self.species == "terminal"):

                    self.locked = False

            return True

        elif (message == "show-hack-panel"):

            # Fetch active map
            m = universe.get_active_map()

            if (self.genus == GENUS_NPC):

                if (self.species == "terminal"):

                    # If we just requested the hack panel, then display it...
                    if (m.hack_panel == None):

                        m.create_hack_panel(self.passcode)

                        # We definitely aren't done yet
                        return False

                    # Otherwise, return whether or not we have dismissed the hack panel yet...
                    else:

                        return m.hack_panel.is_fading()

        elif (message == "set-preferred-target"):

            self.preferred_target_name = param

        elif (message == "assign-territory"):

            self.ai_state.ai_territory = target

            return True

        elif (message == "assign-respawn-region"):

            self.respawn_region_name = target

            return True

        elif (message == "hide"):

            self.set_status(STATUS_INACTIVE)
            self.alive = True

            return True

        elif (message == "activate"):

            """
            if ( not (self.status == STATUS_ACTIVE) ):

                if ( pygame.key.get_pressed()[K_LCTRL] and (self.name == "arrow1") ):

                    logn( "entity debug", self.name )
                    logn( "entity debug", self )
                    logn( "entity debug", "Aborting:  Test." )
                    sys.exit()
            """

            self.set_status(STATUS_ACTIVE)
            self.alive = True

            log2( "Activating '%s'" % self.name )

            return True

        elif (message == "deactivate"):

            self.set_status(STATUS_INACTIVE)
            self.alive = False

            #print self.name
            #print self
            #print 5/0

            return True

        elif (message == "corpse"):

            self.set_status(STATUS_INACTIVE)
            self.alive = False

            self.corpsed = True

            return True

        elif (message == "reanimate"):

            self.set_status(STATUS_INACTIVE)
            self.alive = False

            self.corpsed = False

            self.respawn()

            return True

        elif (message == "fade-out"):

            return self.fade_out()

        elif (message == "fade-in"):

            return self.fade_in()

        elif (message == "lever-position"):

            # This message is for levers only
            if (self.genus == GENUS_LEVER):

                if (param == "left"):
                    self.position = DIR_LEFT

                elif (param == "right"):
                    self.position = DIR_RIGHT

                elif (param == "up"):
                    self.position = DIR_UP

                elif (param == "down"):
                    self.position = DIR_DOWN

            return True

        elif (message == "activate-skill"):

            self.activate_skill(param, control_center, universe, scripted = True)

            return True

        elif (message == "make-disposable"):

            self.is_disposable = True

            return True


        # Change an entity's direction (used for, say, indicator arrows)
        elif (message == "set-direction"):

            # Validate that the given param is valid
            if ( is_numeric(param) ):

                # Cast as int
                param = int(param)

                # Validate that it's a known direction
                if ( param in (DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) ):

                    # Set direction
                    self.set_direction(param)

                else:
                    log( "Warning:  Direction '%s' does not exist!" % param )

            else:
                log( "Warning:  Direction '%s' is not numeric!" % param )

            return True


        # Change an entity's base speed
        elif (message == "set-speed"):

            # Validate that the given param is numeric
            if ( is_numeric(param) ):

                # Set speed according to the given param
                self.set_speed( float(param) )

            # Specify "default" to revert to default speed
            elif ( param == "default" ):

                # Recall the entity's default speed
                self.set_speed(
                    self.get_default_speed()
                )

            return True


        elif (message == "die"):

            self.queue_death_by_cause(DEATH_BY_VAPORIZATION)

            return True


        # Generic return we should never reach
        return True


    # Override these functions in inheriting classes
    def die(self, cause, control_center, universe, with_effects = True, server_approved = None):#, network_controller, universe, p_map, session, with_effects = True, server_approved = None):

        return


    # Check to see if this entity is permanently dead.
    def is_dead(self):

        # Simple corpse check
        return self.corpsed


    def queue_death_by_cause(self, cause):

        # Don't do anything to inactive entities
        if ( self.get_status() == STATUS_ACTIVE ):

            # Queue death
            self.queued_death_by_cause = cause


    def respawn(self):

        return


    # Override this as necessary... if this returns True, then we shouldn't remove the corpsed object yet...
    def twitching(self):

        return ( len(self.particles) > 0 )


    # Entities with shields might survive spikes and bombs...
    def is_protected_by_shield(self, cause, universe):

        # A personal shield can save players from spikes for a while
        if (self.genus == GENUS_PLAYER):

            # Get the amount of shield left
            shield_remaining = int( universe.get_session_variable("core.skills.personal-shield:timer").get_value() )


            # What level of the personal-shield skill is the player using?
            level = int( universe.get_session_variable("core.skills.personal-shield").get_value() )

            # Make sure we have at least level 1 shield... if not, we can't be protected...
            if (level >= 1):

                log( level )

                # Get the stats data for that level of personal-shield from the universe
                stats = universe.get_skill_stats().get_skill_stats_by_level("personal-shield", level)

                log( stats )


                # What's the penalty to the timer per damage point?
                penalty_per_damage_point = int( stats.get_modifier_by_name("timer-drain-penalty-per-damage-point") )

                # We must reduce the current shield timer by that amount for each damage point.  Various
                # causes of death have different damage point values...
                damage_points = DAMAGE_POINTS_BY_CAUSE[cause]

                # Calculate new shield remaining value
                shield_remaining -= penalty_per_damage_point * damage_points


                # Track it via session
                universe.set_session_variable("core.skills.personal-shield:timer", "%d" % shield_remaining)


                # Update "has shield" flag
                self.has_shield = (shield_remaining > 0)


                # If we have shield remaining, we're protected.  Otherwise...
                return (shield_remaining > 0)            


            # Unfortunately, we don't even have the personal-shield skill...
            else:
                return False

        # Non-player entities are never (?) protected by a shield.
        else:
            return False

    def do_gravity(self, dy, universe, force_drop = False):

        if (not self.ai_state.ai_is_trapped):

            if ( self.get_x() % TILE_WIDTH == 0 ):

                self.check_for_dig_trap(self.get_x(), (self.get_y() + self.height), universe)


        # Ignore gravity while on a ladder or a monkey bar...
        #if (self.is_climbing or (self.is_swinging and (not force_drop)) ):
        #    return

        # Also ignore gravity for enemies who are trapped
        if (self.ai_state.ai_is_trapped):

            #log2( "enemy '%s' is trapped, aborting gravity..." % self.name )
            return


        # Fetch the active map
        m = universe.get_active_map()



        if (dy > 0):

            self.can_move = False
            self.is_swinging = False


            # Before applying gravity, let's see if we're in position to swing on a monkey bar.
            if (self.knows_how_to_hang):

                # As long as the entity hasn't indicated a desire to fall off of a potential monkey bar, keep checking for a monkey bar
                if (not force_drop):

                    # Is this entity currently in position to already hang from a monkey bar?
                    if ( self.get_y() % TILE_HEIGHT == 0 ):

                        # If so, is this entity indeed hanging from a monkey bar?
                        if ( m.master_plane.check_monkeybar_exists_in_rect( self.get_rect() ) ):

                            # Movement is okay
                            self.can_move = True

                            # Is hanging on the monkey bar
                            self.is_swinging = True


                            # Don't apply gravity in this situation
                            return False


            # Is the entity already on a ladder?
            already_on_ladder = False

            if (self.knows_how_to_hang):

                if ( m.master_plane.check_ladder_exists_in_rect( offset_rect(self.get_rect(), h = 1) ) ):
                    already_on_ladder = True


            # If we are already overlapping any entity, then we won't factor them into "landed on them" calculations...
            overlapping_entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_gravity, self ).get_results()


            # Recall the previous tile position of the player (top edge)
            ty1 = int( self.get_y() / TILE_HEIGHT )

            # Apply gravity
            self.y += dy

            # Determine the new tile position
            ty2 = int( self.get_y() / TILE_HEIGHT )


            # See we entities we may have landed on...
            entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_gravity, self ).filter_out_entities(overlapping_entities).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, Y_AXIS).get_results()

            if ( len(entities) > 0 ):

                self.y -= dy
                self.can_move = True

                return False

            elif ( m.master_plane.check_fall_collision_in_rect(self.get_rect(), self.ai_state.ai_trap_exception) ):

                if (already_on_ladder):

                    self.y -= dy

                else:

                    self.y = int(self.get_y() / TILE_HEIGHT) * TILE_HEIGHT

                self.can_move = True

                return False

            elif ( m.master_plane.check_deadly_fall_collision_in_rect(self.get_rect(), self.ai_state.ai_trap_exception) ):

                # In case they survive
                self.y = int(self.get_y() / TILE_HEIGHT) * TILE_HEIGHT


                # Good news, entity can move.
                self.can_move = True

                # Bad news, entity is dead
                self.queue_death_by_cause(DEATH_BY_DEADLY_TILE)


                return False

            # If gravity successfully pulled the player down, remove any decimal value from the x-axis, to get a perfect alignment.
            else:

                self.x = int(self.get_x())

                # If the entity fell to a new row, it might have gone slightly past a monkey bar.
                # In that case, we should check the even row interval for a monkey bar and clamp gravity's influence if we find one...
                if (ty2 > ty1):

                    # Can this entity hang from monkey bars?
                    if (self.knows_how_to_hang):

                        # If so, is this entity indeed hanging from a monkey bar?
                        if ( m.master_plane.check_monkeybar_exists_in_rect( (self.get_x(), (ty2 * TILE_HEIGHT), self.width, 1) ) ):

                            # Clamp gravity, in case we overshot the exact monkey bar location
                            self.y = (ty2 * TILE_HEIGHT)


                            # Movement is okay
                            self.can_move = True

                            # Is hanging on the monkey bar
                            self.is_swinging = True


                            # Don't apply gravity in this situation
                            return False


                return True


    # Sometimes we'll need to check to see if we were allowed to walk beyond a given column.
    def can_walk_over_tile(self, tx, ty, m):

        # If the player has activated a personal shield, then they can walk on deadly tiles.
        #if ( (self.name == "player1") and ( int( universe.get_session_variable("core.skills.personal-shield:timer").get_value() ) > 0 ) ):
        if (self.has_shield):

            # Just check deadly tile here; return True if it's the first match.
            if ( m.master_plane.check_collision(tx, ty) in (COLLISION_DEADLY,) ):

                # Shortcut
                return True


        # Not standing on some sort of solid ground / tile?
        if ( not m.master_plane.check_collision(tx, ty) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_LADDER, COLLISION_BRIDGE) ):

            # Next chance... ladder or monkey bar to cross the gap
            if ( not m.master_plane.check_collision(tx, ty - 1) in (COLLISION_LADDER, COLLISION_MONKEYBAR) ):

                # Another chance... sometimes enemies can walk on "air" if that "air" is a trap they just escaped...
                if ( not self.can_find_escaped_dig_trap(tx, ty, m) ):

                    # Last chance, perhaps an entity exists within the empty air that we can walk on top of?
                    # They have to be flush with the top of the tile in order for the current entity to walk on top of them.  (Thus the height of 1.)
                    if ( m.count_entities_in_rect( (tx * TILE_WIDTH, ty * TILE_HEIGHT, TILE_WIDTH, 1) ) == 0 ):

                        return False

        # Success
        return True


    # Move by some amount (dx, dy) on some map m
    def move(self, dx, dy, universe, determined = None, pushed = False, recursive = False):

        # Fetch the active map
        m = universe.get_active_map()


        if (not self.can_move):

            # If the entity is trapped and the movement is vertical, we'll allow it...
            # they're probably just trying to fall into or out of the trap...
            if (self.ai_state.ai_is_trapped and (dx == 0)):
                pass

            # Also, if it's a planar shift pushing the entity, I'll always allow it...
            elif (pushed):
                pass

            else:
                #print "self.can_move is False"
                return False

        elif (self.ai_state.ai_frozen):
            pass


        # Move up
        if (dy < 0):

            # Remember last attempted vertical move
            self.ai_state.last_attempted_vertical_move = DIR_UP


            # Special case for trapped enemies (they won't be using ladders at all...)
            if (self.ai_state.ai_is_trapped):

                self.y += dy


                entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                if ( len(entities) > 0 ):

                    self.y -= dy

                    # Dang.  Back into the trap, lol!
                    self.ai_state.ai_is_trapped = True

                    self.ai_state.ai_trap_time_remaining = AI_MAX_TRAP_TIME

                    # Remember the location as the trap exception for when we climb out...
                    # We already know which trap we were in; we never escaped...
                    # Let's do the enemy the small favor of replenishing their exception time, as if
                    # they ever had the chance to use it, ha ha ha...
                    self.ai_state.ai_trap_exception_time = AI_MAX_TRAP_EXCEPTION_TIME + 0 # A little bonus for the enemy, ha ha ha ha ha

                    return False


                elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    self.y = int( (self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT
                    return False

                # Successful move?
                else:

                    self.set_direction(DIR_UP)
                    self.animate()

                    return True


            # If we last moved left, then we'll prefer a ladder on the left...
            elif (self.ai_state.last_lateral_move == DIR_LEFT):

                # Get left border rect
                r_left_border = self.get_left_border()
                r_right_border = self.get_right_border()

                # See if there's a ladder on the left...
                if ( m.master_plane.check_ladder_exists_in_rect(r_left_border) ):

                    # If so, are we in perfect alignment with the ladder?
                    if (self.get_x() % TILE_WIDTH == 0):

                        # Perfect alignment
                        self.x = self.get_x()


                        # Try to move
                        self.y += dy


                        entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                        # We probably can't do this if we're hitting another entity...
                        if ( len(entities) > 0 ):

                            # Send touch event to each entity
                            for entity in entities:

                                # Handle touch
                                entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                            self.y -= dy
                            return False


                        elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):
                            self.y = int( (self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT
                            return False

                        # Successful move?
                        else:

                            self.ai_state.last_vertical_move = DIR_UP

                            self.set_direction(DIR_UP)
                            self.animate()

                            # Perhaps during the climb, we climbed a little bit above the end of a ladder
                            # (due to movement speed).  If we did this and there wasn't actually another ladder to climb,
                            # then we need to clamp the upward movement...
                            (last_ty, current_ty) = (
                                int(self.y - dy) / TILE_HEIGHT,
                                int(self.y) / TILE_HEIGHT
                            )

                            # Moved up to a new tile, potentially slightly skipping empty air onto a separate ladder?
                            if (last_ty > current_ty):

                                # Make sure a ladder exists on the tile we were leaving...
                                if ( not m.master_plane.check_ladder_exists_in_rect( (r_left_border[0], (last_ty * TILE_HEIGHT), r_left_border[2], TILE_HEIGHT) ) ):

                                    # Clamp vertical movement.  The move is still perfectly valid, but we can't skip up farther than the ladder lets us...
                                    self.y = (last_ty * TILE_HEIGHT)


                            return True


                    # If not, let's move to the left a little bit...
                    else:

                        x_target = int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH

                        result = self.seek_location(
                            x_target, self.get_y(), self.speed, 0, universe, recursive
                        )

                        if (result):

                            self.set_direction(DIR_LEFT)
                            self.animate()

                        return result


                # If we can't find a ladder on the left, we'll settle for one on the right...
                elif ( m.master_plane.check_ladder_exists_in_rect(r_right_border) ):

                    # Are we aligned?
                    if (self.get_x() % TILE_WIDTH == 0):

                        # Perfect alignment
                        self.x = self.get_x()


                        # Try to move
                        self.y += dy


                        entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                        # We probably can't do this if we're hitting another entity...
                        if ( len(entities) > 0 ):

                            # Send touch event to each entity
                            for entity in entities:

                                # Handle touch
                                entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                            self.y -= dy
                            return False


                        elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                            self.y = int( (self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT
                            return False

                        # Successful move?
                        else:

                            self.ai_state.last_vertical_move = DIR_UP

                            self.set_direction(DIR_UP)
                            self.animate()

                            # Perhaps during the climb, we climbed a little bit above the end of a ladder
                            # (due to movement speed).  If we did this and there wasn't actually another ladder to climb,
                            # then we need to clamp the upward movement...
                            (last_ty, current_ty) = (
                                int(self.y - dy) / TILE_HEIGHT,
                                int(self.y) / TILE_HEIGHT
                            )

                            # Moved up to a new tile, potentially slightly skipping empty air onto a separate ladder?
                            if (last_ty > current_ty):

                                # Make sure a ladder exists on the tile we were leaving...
                                if ( not m.master_plane.check_ladder_exists_in_rect( (r_right_border[0], (last_ty * TILE_HEIGHT), r_right_border[2], TILE_HEIGHT) ) ):

                                    # Clamp vertical movement.  The move is still perfectly valid, but we can't skip up farther than the ladder lets us...
                                    self.y = (last_ty * TILE_HEIGHT)

                            return True

                    # Nope; let's move into position...
                    else:

                        x_target = int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH

                        result = self.seek_location(
                            x_target, self.get_y(), self.speed, 0, universe, recursive
                        )

                        if (result):

                            self.set_direction(DIR_RIGHT)
                            self.animate()

                        return result

                # When all else fails, a player entity might move laterally, trying to find a ladder...
                elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                    # If all else fails, we'll move laterally in the last-known direction...
                    if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                        # Last attempted to move left?
                        if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                            # Try to move left
                            return self.move(-self.speed, 0, universe, recursive = True)

                        # Last attempted right, then...
                        else:

                            # Try to move right
                            return self.move(self.speed, 0, universe, recursive = True)


            # Otherwise, we'll prefer a ladder on the right...
            elif (self.ai_state.last_lateral_move == DIR_RIGHT):

                r_left_border = self.get_left_border()
                r_right_border = self.get_right_border()

                # See if there's a ladder on the right...
                if ( m.master_plane.check_ladder_exists_in_rect(r_right_border) ):

                    # If so, are we in perfect alignment with the ladder?
                    if (self.get_x() % TILE_WIDTH == 0):

                        # Perfect alignment
                        self.x = self.get_x()

                        # Try to move
                        self.y += dy


                        entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                        # We probably can't do this if we're hitting another entity...
                        if ( len(entities) > 0 ):

                            # Send touch event to each entity
                            for entity in entities:

                                # Handle touch
                                entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                            self.y -= dy
                            return False

                        elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                            self.y = int( (self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT
                            return False

                        # Successful move?
                        else:

                            self.ai_state.last_vertical_move = DIR_UP

                            self.set_direction(DIR_UP)
                            self.animate()

                            # Perhaps during the climb, we climbed a little bit above the end of a ladder
                            # (due to movement speed).  If we did this and there wasn't actually another ladder to climb,
                            # then we need to clamp the upward movement...
                            (last_ty, current_ty) = (
                                int(self.y - dy) / TILE_HEIGHT,
                                int(self.y) / TILE_HEIGHT
                            )

                            # Moved up to a new tile, potentially slightly skipping empty air onto a separate ladder?
                            if (last_ty > current_ty):

                                # Make sure a ladder exists on the tile we were leaving...
                                if ( not m.master_plane.check_ladder_exists_in_rect( (r_right_border[0], (last_ty * TILE_HEIGHT), r_right_border[2], TILE_HEIGHT) ) ):

                                    # Clamp vertical movement.  The move is still perfectly valid, but we can't skip up farther than the ladder lets us...
                                    self.y = (last_ty * TILE_HEIGHT)

                            return True


                    # If not, let's move to the right a little bit...
                    else:

                        x_target = int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH

                        result = self.seek_location(
                            x_target, self.get_y(), self.speed, 0, universe, recursive
                        )

                        if (result):

                            self.set_direction(DIR_RIGHT)
                            self.animate()

                        return result


                # If we can't find a ladder on the right, we'll settle for one on the left...
                elif ( m.master_plane.check_ladder_exists_in_rect(r_left_border) ):

                    # Are we aligned?
                    if (self.get_x() % TILE_WIDTH == 0):

                        # Perfect alignment
                        self.x = self.get_x()


                        # Try to move
                        self.y += dy


                        entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results() # (?) used to be X...

                        # We probably can't do this if we're hitting another entity...
                        if ( len(entities) > 0 ):

                            # Send touch event to each entity
                            for entity in entities:

                                # Handle touch
                                entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                            self.y -= dy
                            return False


                        elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                            self.y = int( (self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT
                            return False

                        # Successful move?
                        else:

                            self.ai_state.last_vertical_move = DIR_UP

                            self.set_direction(DIR_UP)
                            self.animate()

                            # Perhaps during the climb, we climbed a little bit above the end of a ladder
                            # (due to movement speed).  If we did this and there wasn't actually another ladder to climb,
                            # then we need to clamp the upward movement...
                            (last_ty, current_ty) = (
                                int(self.y - dy) / TILE_HEIGHT,
                                int(self.y) / TILE_HEIGHT
                            )

                            # Moved up to a new tile, potentially slightly skipping empty air onto a separate ladder?
                            if (last_ty > current_ty):

                                # Make sure a ladder exists on the tile we were leaving...
                                if ( not m.master_plane.check_ladder_exists_in_rect( (r_left_border[0], (last_ty * TILE_HEIGHT), r_left_border[2], TILE_HEIGHT) ) ):

                                    # Clamp vertical movement.  The move is still perfectly valid, but we can't skip up farther than the ladder lets us...
                                    self.y = (last_ty * TILE_HEIGHT)

                            return True

                    # Nope; let's move into position...
                    else:

                        x_target = int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH

                        result = self.seek_location(
                            x_target, self.get_y(), self.speed, 0, universe, recursive
                        )

                        if (result):

                            self.set_direction(DIR_LEFT)
                            self.animate()

                        return result

                # When all else fails, a player entity might move laterally, trying to find a ladder...
                elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                    # If all else fails, we'll move laterally in the last-known direction...
                    if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                        # Last attempted to move left?
                        if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                            # Try to move left
                            return self.move(-self.speed, 0, universe, recursive = True)

                        # Last attempted right, then...
                        else:

                            # Try to move right
                            return self.move(self.speed, 0, universe, recursive = True)


        # Move down
        elif (dy > 0):

            self.ai_state.last_attempted_vertical_move = DIR_DOWN


            # Special case for trapped enemies (they won't be using ladders at all...)
            if (self.ai_state.ai_is_trapped):

                # Fall further into the trap
                self.y += dy


                # Probably wouldn't collide with an entity in this scenario, but let's check...
                entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                # Entity collision?
                if ( len(entities) > 0 ):

                    # Abort
                    self.y -= dy
                    return False

                # Tile collision check
                elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    # Clamp movement, return "failure" (didn't complete full move)
                    self.y = int( (self.get_y() / TILE_HEIGHT) ) * TILE_HEIGHT
                    return False

                # Successful move?
                else:

                    # Set direction to down and animate
                    self.set_direction(DIR_DOWN)
                    self.animate()

                    # Return success
                    return True


            # Not a trapped enemy
            else:

                # Is the entity aligned evenly with a tile column?
                if ( self.get_x() % TILE_WIDTH == 0 ):

                    # Any entity (player, enemy, etc.) can move down if they're on a ladder.
                    # We can simply use left border because of the perfect alignment.
                    if ( m.master_plane.check_ladder_exists_in_rect( offset_rect( self.get_left_border(), h = 1 ) ) ):

                        # Round
                        self.x = self.get_x()

                        # Try to move
                        self.y += dy


                        # Find any relevant entity we're now colliding wtih...
                        entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                        # We probably can't do this if we're hitting another entity...
                        if ( len(entities) > 0 ):

                            # Send touch event to each entity
                            for entity in entities:

                                # Handle touch
                                entity.handle_entity_touch(self, control_center = None, universe = universe) # ?

                            # Abort move
                            self.y -= dy

                            # Return failure
                            return False

                        # Tile collision check
                        elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                            # Clamp movement
                            self.y = int( (self.get_y() / TILE_HEIGHT) ) * TILE_HEIGHT

                            # Return failure
                            return False

                        # Successful move?
                        else:

                            # Remember last vertical movement direction
                            self.ai_state.last_vertical_move = DIR_DOWN

                            # Set direction to down, animate
                            self.set_direction(DIR_DOWN)
                            self.animate()

                            # Return success
                            return True

                    # If we're not on a ladder, perhaps we are swinging from a monkeybar...
                    elif ( self.is_swinging ):

                        # Simply apply gravity
                        result = self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)

                        # Change direction if successful
                        if (result):

                            # Set direction and animate
                            self.set_direction(DIR_DOWN)
                            self.animate()

                        # Return result
                        return result

                    # When all else fails, a player entity might move laterally, trying to find a ladder...
                    elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                        # This logic only applies if the player last moved to the left/right
                        if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                            # Last attempted to move left?
                            if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                                # Try to move left
                                return self.move(-self.speed, 0, universe, recursive = True)

                            # Last attempted right, then...
                            else:

                                # Try to move right
                                return self.move(self.speed, 0, universe, recursive = True)


                # If the entity is not aligned on a column, we will potentially need to align first
                else:

                    # Last moved left?
                    if (self.ai_state.last_lateral_move == DIR_LEFT):

                        # If the player is currently swinging on a monkey bar, then they can (try to) drop down
                        if ( self.is_swinging ):

                            # Player entities can try to drop from any x location
                            if ( self.genus == GENUS_PLAYER ):

                                # Try to force gravity drop
                                result = self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)

                                # If we couldn't drop, let's try to get into perfect alignment to drop next frame...
                                if (not result):

                                    result = self.seek_location(
                                        int( self.get_x() / TILE_WIDTH ) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                                    )

                                    if (result):

                                        self.set_direction(DIR_LEFT)
                                        self.animate()

                                    return result

                                # Drop succeeded
                                else:
                                    return result

                            # All other entity types must seek an even column alignment
                            else:

                                # Seek the column to the left
                                result = self.seek_location(
                                    int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                                )

                                # A successful move will animate the character
                                if (result):

                                    # Set direction and animate
                                    self.set_direction(DIR_LEFT)
                                    self.animate()

                                # Return result
                                return result


                        # If the player isn't actively swinging on a monkey bar, let's see if there's a ladder/monkey bar just to the left to auto target...
                        elif ( m.master_plane.check_ladder_or_monkeybar_exists_in_rect( offset_rect( self.get_left_border(), h = 1 ) ) ):

                            # Seek that column to the lefl
                            result = self.seek_location(
                                int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                            )

                            # A successful move will animate the character
                            if (result):

                                # Set direction and animate
                                self.set_direction(DIR_LEFT)
                                self.animate()

                            # Return result
                            return result

                        # Perhaps the player slightly overshot a monkeybar/ladder, and they really want to shade back to the right to go down...
                        elif ( m.master_plane.check_ladder_or_monkeybar_exists_in_rect( offset_rect( self.get_right_border(), h = 1 ) ) ):

                            # Seek that column to the lefl
                            result = self.seek_location(
                                int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                            )

                            # A successful move will animate the character
                            if (result):

                                # Set direction and animate
                                self.set_direction(DIR_LEFT)
                                self.animate()

                            # Return result
                            return result

                        # When all else fails, a player entity might move laterally, trying to find a ladder...
                        elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                            # This logic only applies if the player last moved to the left/right
                            if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                                # Last attempted to move left?
                                if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                                    # Try to move left
                                    return self.move(-self.speed, 0, universe, recursive = True)

                                # Last attempted right, then...
                                else:

                                    # Try to move right
                                    return self.move(self.speed, 0, universe, recursive = True)

                    # Last moved right?
                    elif (self.ai_state.last_lateral_move == DIR_RIGHT):

                        # If the player is currently swinging on a monkey bar, then they can (try to) drop down
                        if ( self.is_swinging ):

                            # Player entities can try to drop from any x location
                            if ( self.genus == GENUS_PLAYER ):

                                # Try to force gravity drop
                                result = self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)

                                # If we couldn't drop, let's try to get into perfect alignment to drop next frame...
                                if (not result):

                                    local_result = self.seek_location(
                                        int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                                    )

                                    if (local_result):

                                        self.set_direction(DIR_RIGHT)
                                        self.animate()

                                    return local_result

                                # Drop succeeded
                                else:
                                    return result

                            # All other entity types must seek an even column alignment
                            else:

                                # Seek the column to the left
                                result = self.seek_location(
                                    int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                                )

                                # A successful move will animate the character
                                if (result):

                                    # Set direction and animate
                                    self.set_direction(DIR_RIGHT)
                                    self.animate()

                                # Return result
                                return result


                        # If the player isn't actively swinging on a monkey bar, let's see if there's a ladder/monkey bar just to the left to auto target...
                        elif ( m.master_plane.check_ladder_or_monkeybar_exists_in_rect( offset_rect( self.get_right_border(), h = 1 ) ) ):

                            # Seek that column to the lefl
                            result = self.seek_location(
                                int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                            )

                            # A successful move will animate the character
                            if (result):

                                # Set direction and animate
                                self.set_direction(DIR_RIGHT)
                                self.animate()

                            # Return result
                            return result

                        # Perhaps the player slightly overshot a monkeybar/ladder, and they really want to shade back to the left to go down...
                        elif ( m.master_plane.check_ladder_or_monkeybar_exists_in_rect( offset_rect( self.get_left_border(), h = 1 ) ) ):

                            # Seek that column to the lefl
                            result = self.seek_location(
                                int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH, self.get_y(), self.speed, 0, universe, recursive
                            )

                            # A successful move will animate the character
                            if (result):

                                # Set direction and animate
                                self.set_direction(DIR_RIGHT)
                                self.animate()

                            # Return result
                            return result

                        # When all else fails, a player entity might move laterally, trying to find a ladder...
                        elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                            # This logic only applies if the player last moved to the left/right
                            if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                                # Last attempted to move left?
                                if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                                    # Try to move left
                                    return self.move(-self.speed, 0, universe, recursive = True)

                                # Last attempted right, then...
                                else:

                                    # Try to move right
                                    return self.move(self.speed, 0, universe, recursive = True)


                """
                # If we last moved left, then we'll prefer a ladder on the left...
                if (self.ai_state.last_lateral_move == DIR_LEFT):


                        # If not, let's move to the left a little bit...
                        else:

                            x_target = int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH

                            result = self.move(-self.speed, 0, universe)

                            # Don't overshoot the ladder...
                            if (self.x < x_target):
                                self.x = x_target

                            if (result):

                                self.set_direction(DIR_LEFT)
                                self.animate()

                            return result


                    # If we can't find a ladder on the left, we'll settle for one on the right...
                    elif ( m.master_plane.check_ladder_exists_in_rect( offset_rect(self.get_right_border(), h = 1) ) ):

                        # Are we aligned?
                        if (self.get_x() % TILE_WIDTH == 0):

                            # Perfect alignment
                            self.x = self.get_x()


                            # Try to move
                            self.y += dy


                            entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                            # We probably can't do this if we're hitting another entity...
                            if ( len(entities) > 0 ):

                                # Send touch event to each entity
                                for entity in entities:

                                    # Handle touch
                                    entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                                self.y -= dy
                                return False

                            elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):
                                self.y = int( (self.get_y() / TILE_HEIGHT) ) * TILE_HEIGHT
                                return False

                            # Successful move?
                            else:

                                self.ai_state.last_vertical_move = DIR_DOWN

                                self.set_direction(DIR_DOWN)
                                self.animate()

                                return True

                        # Nope; let's move into position...
                        else:

                            x_target = int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH

                            result = self.move(self.speed, 0, universe)

                            # Do not overshoot the ladder!
                            if (self.x > x_target):
                                self.x = x_target

                            if (result):

                                self.set_direction(DIR_RIGHT)
                                self.animate()

                            return result


                    # If we didn't find any ladders, we can at least try dropping from a monkey bar...
                    elif ( self.is_swinging ):#(self.get_y() % TILE_HEIGHT == 0) ):

                        # A player can (try to) drop immediately, irregardless of current x alignment!
                        if (self.genus == GENUS_PLAYER):

                            # Try to force gravity drop
                            result = self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)


                            # If we couldn't drop, let's try to get into perfect alignment to drop next frame...
                            if (not result):

                                x_target = int(self.get_x() / TILE_WIDTH) * TILE_WIDTH

                                local_result = self.move(-self.speed, 0, universe)

                                # Don't overshoot
                                if (self.x < x_target):
                                    self.x = x_target

                                if (local_result):

                                    self.set_direction(DIR_LEFT)
                                    self.animate()


                            # Return the result for the original "move down" request
                            return result


                        # Enemies (or NPCs) can only drop when evenly aligned with a column
                        elif ( self.genus in (GENUS_ENEMY, GENUS_NPC) ):

                            # Ok, enemy can drop...
                            if (self.get_x() % TILE_WIDTH == 0):

                                return self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)


                            # No; we need to try to align evenly...
                            elif (self.ai_state.last_lateral_move == DIR_LEFT):

                                x_target = int(self.get_x() / TILE_WIDTH) * TILE_WIDTH

                                result = self.move(-self.speed, 0, universe)

                                # Don't overshoot
                                if (self.x < x_target):
                                    self.x = x_target

                                if (result):

                                    self.set_direction(DIR_LEFT)
                                    self.animate()

                                return result

                            elif (self.ai_state.last_lateral_move == DIR_RIGHT):

                                x_target = (int(self.get_x() / TILE_WIDTH) * TILE_WIDTH) + TILE_WIDTH

                                result = self.move(self.speed, 0, universe)

                                # Don't overshoot
                                if (self.x > x_target):
                                    self.x = x_target

                                if (result):

                                    self.set_direction(DIR_RIGHT)
                                    self.animate()

                                return result

                    # When all else fails, a player entity might move laterally, trying to find a ladder...
                    elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                        # If all else fails, we'll move laterally in the last-known direction...
                        if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                            # Last attempted to move left?
                            if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                                # Try to move left
                                return self.move(-self.speed, 0, universe)

                            # Last attempted right, then...
                            else:

                                # Try to move right
                                return self.move(self.speed, 0, universe)


                # Otherwise, we'll prefer a ladder on the right...
                elif (self.ai_state.last_lateral_move == DIR_RIGHT):

                    # See if there's a ladder on the right...
                    if ( m.master_plane.check_ladder_exists_in_rect( offset_rect(self.get_right_border(), h = 1) ) ):

                        # If so, are we in perfect alignment with the ladder?
                        if (self.get_x() % TILE_WIDTH == 0):

                            # Perfect alignment
                            self.x = self.get_x()

                            # Try to move
                            self.y += dy


                            entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                            # We probably can't do this if we're hitting another entity...
                            if ( len(entities) > 0 ):

                                # Send touch event to each entity
                                for entity in entities:

                                    # Handle touch
                                    entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                                self.y -= dy
                                return False

                            elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):
                                self.y = int( (self.get_y() / TILE_HEIGHT) ) * TILE_HEIGHT
                                return False

                            # Successful move?
                            else:

                                self.ai_state.last_vertical_move = DIR_DOWN

                                self.set_direction(DIR_DOWN)
                                self.animate()

                                return True


                        # If not, let's move to the left a little bit...
                        else:

                            x_target = int(self.get_right_border()[0] / TILE_WIDTH) * TILE_WIDTH

                            result = self.move(self.speed, 0, universe)

                            # Don't overshoot the ladder...
                            if (self.x > x_target):
                                self.x = x_target

                            if (result):

                                self.set_direction(DIR_RIGHT)
                                self.animate()

                            return result


                    # If we can't find a ladder on the right, we'll settle for one on the left...
                    elif ( m.master_plane.check_ladder_exists_in_rect( offset_rect(self.get_left_border(), h = 1) ) ):

                        # Are we aligned?
                        if (self.get_x() % TILE_WIDTH == 0):

                            # Perfect alignment
                            self.x = self.get_x()


                            # Try to move
                            self.y += dy


                            entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, Y_AXIS).get_results()

                            # We probably can't do this if we're hitting another entity...
                            if ( len(entities) > 0 ):

                                # Send touch event to each entity
                                for entity in entities:

                                    # Handle touch
                                    entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                                self.y -= dy
                                return False

                            elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                                self.y = int( (self.get_y() / TILE_HEIGHT) ) * TILE_HEIGHT
                                return False

                            # Successful move?
                            else:

                                self.ai_state.last_vertical_move = DIR_DOWN

                                self.set_direction(DIR_DOWN)
                                self.animate()

                                return True

                        # Nope; let's move into position...
                        else:

                            x_target = int(self.get_left_border()[0] / TILE_WIDTH) * TILE_WIDTH

                            result = self.move(-self.speed, 0, universe)

                            # Do not overshoot the ladder!
                            if (self.x < x_target):
                                self.x = x_target

                            if (result):

                                self.set_direction(DIR_LEFT)
                                self.animate()

                            return result



                    # If we didn't find any ladders, we can at least try dropping from a monkey bar...
                    elif ( self.is_swinging ):#(self.get_y() % TILE_HEIGHT == 0) ):

                        # A player can (try to) drop immediately, irregardless of current x alignment!
                        if (self.genus == GENUS_PLAYER):

                            # Try to force gravity drop
                            result = self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)


                            # If we couldn't drop, let's try to get into perfect alignment to drop next frame...
                            if (not result):

                                x_target = (int(self.get_x() / TILE_WIDTH) * TILE_WIDTH) + TILE_WIDTH

                                local_result = self.move(self.speed, 0, universe)

                                # Don't overshoot
                                if (self.x > x_target):
                                    self.x = x_target

                                if (local_result):

                                    self.set_direction(DIR_RIGHT)
                                    self.animate()


                            # Return the result for the original "move down" request
                            return result


                        # Enemies and NPCs can only drop when evenly aligned with a column
                        elif (self.genus in (GENUS_ENEMY, GENUS_NPC)):

                            # Ok, he can drop...
                            if (self.get_x() % TILE_WIDTH == 0):
                                self.do_gravity(RATE_OF_GRAVITY, universe, force_drop = True)


                            # No; we need to try to align evenly...
                            elif (self.ai_state.last_lateral_move == DIR_LEFT):

                                x_target = int(self.get_x() / TILE_WIDTH) * TILE_WIDTH

                                result = self.move(-self.speed, 0, universe)

                                # Don't overshoot
                                if (self.x < x_target):
                                    self.x = x_target

                                if (result):

                                    self.set_direction(DIR_LEFT)
                                    self.animate()

                                return result

                            elif (self.ai_state.last_lateral_move == DIR_RIGHT):

                                x_target = (int(self.get_x() / TILE_WIDTH) * TILE_WIDTH) + TILE_WIDTH

                                result = self.move(self.speed, 0, universe)

                                # Don't overshoot
                                if (self.x > x_target):
                                    self.x = x_target

                                if (result):

                                    self.set_direction(DIR_RIGHT)
                                    self.animate()

                                return result

                    # When all else fails, a player entity might move laterally, trying to find a ladder...
                    elif ( (not recursive) and (self.genus == GENUS_PLAYER) ):

                        # If all else fails, we'll move laterally in the last-known direction...
                        if ( self.get_direction() in (DIR_LEFT, DIR_RIGHT) ):

                            # Last attempted to move left?
                            if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                                # Try to move left
                                return self.move(-self.speed, 0, universe)

                            # Last attempted right, then...
                            else:

                                # Try to move right
                                return self.move(self.speed, 0, universe)
                """




        # Preserve precise vertical alignment
        elif ( dx != 0 and ( (self.get_y() % TILE_HEIGHT) != 0 ) ):

            # We want to move up a little more?
            if (self.ai_state.last_vertical_move == DIR_UP):

                y_target = int(self.get_y() / TILE_HEIGHT) * TILE_HEIGHT

                result = self.seek_location(
                    self.get_x(), y_target, 0, self.speed, universe, recursive
                )

                if (result):

                    self.set_direction(DIR_UP)
                    self.animate()

                return result


            # No; let's go down a little farther...
            elif (self.ai_state.last_vertical_move == DIR_DOWN):

                y_target = (int(self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT

                result = self.seek_location(
                    self.get_x(), y_target, 0, self.speed, universe, recursive
                )

                if (result):

                    self.set_direction(DIR_DOWN)
                    self.animate()

                return result

        elif (dx != 0):

            # Move left
            if (dx < 0):

                # Remember last attempted lateral move
                self.ai_state.last_attempted_lateral_move = DIR_LEFT


                # Previous tile position (left side of sprite)
                tx1 = int( self.get_x() / TILE_WIDTH )

                # Perform movement
                self.x += dx

                # New tile position (left side of sprite)
                tx2 = int( self.get_x() / TILE_WIDTH )


                # If the entity moved to a new column, we need to make sure they didn't
                # "skip over" an empty space without the aid of a monkey bar, etc.
                if (tx2 < tx1):

                    # I used to do this first, why...?
                    #self.check_for_dig_trap( (self.get_x() + (self.width - 1)), (self.get_y() + self.height), universe )

                    # Get the row index below the entity (what they should be standing on, in the column on the sprite's right edge)
                    ty = int( ( self.get_y() + self.height - 1 ) / TILE_HEIGHT ) + 1

                    # Check tile walkability
                    if ( not self.can_walk_over_tile(tx1, ty, m) ):

                        # We can not cross any farther than the drop point; we must adjust the entity location to the column we skipped a little ways past
                        self.x = (tx1 * TILE_WIDTH)


                # Check for entity collisions first
                entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, X_AXIS).get_results()

                # We probably can't do this if we're hitting another entity...
                if ( len(entities) > 0 ):

                    # Send touch event to each entity
                    for entity in entities:

                        # Handle touch
                        entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                    # Correct as far as we need to, to avoid overlapping any colliding entity
                    self.x = self.get_entity_list_max_x(entities)


                    # An enemy that bumps into someone will eventually prefer to turn around; we achieve this
                    # by pretending his last attempted lateral move went the other way...
                    if (self.genus == GENUS_ENEMY):

                        # Losing patience
                        self.ai_state.ai_patience -= 1

                        # Got no time for this, man!
                        if (self.ai_state.ai_patience <= 0):

                            # Prepare for next time
                            self.ai_state.ai_patience = AI_MAX_PATIENCE

                            # This will force AI characters to try to find another path
                            self.ai_state.last_attempted_lateral_move = DIR_RIGHT

                    # Move failed (at least in part)
                    return False

                # If we didn't hit another entity, restore patience...
                else:
                    self.ai_state.ai_patience = AI_MAX_PATIENCE


                if ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    # If we hit a wall... did that wall have spikes?
                    if ( m.master_plane.check_deadly_collision_in_rect_from_direction( self.get_rect(), DIR_RIGHT ) ):

                        # Go ahead and correct the x value...
                        self.x = int( (self.get_x() / TILE_WIDTH) + 1) * TILE_WIDTH

                        # Entity must die...
                        self.queue_death_by_cause(DEATH_BY_DEADLY_TILE)

                    # If not, handle logic normally...
                    else:

                        self.x = int( (self.get_x() / TILE_WIDTH) + 1) * TILE_WIDTH


                    # Move (kind of) failed
                    return False


                # If we made it this far, we know we made a successful move
                self.ai_state.last_lateral_move = DIR_LEFT

                # Update new direction
                self.set_direction(DIR_LEFT)

                # Animate sprite
                self.animate()


                # Success!
                return True


            # Move right
            elif (dx > 0):

                # Remember last attempted lateral move
                self.ai_state.last_attempted_lateral_move = DIR_RIGHT


                # Previous tile position (right side of sprite)
                tx1 = int( ( self.get_x() + self.width - 1 ) / TILE_WIDTH )

                # Perform movement
                self.x += dx

                # New tile position (right side of sprite)
                tx2 = int( ( self.get_x() + self.width - 1 ) / TILE_WIDTH )


                # If the entity moved to a new column, we need to make sure they didn't
                # "skip over" an empty space without the aid of a monkey bar, etc.
                if (tx2 > tx1):

                    # I used to do this first, why...?
                    #self.check_for_dig_trap( (self.get_x() + (self.width - 1)), (self.get_y() + self.height), universe )

                    # Get the row index below the entity (what they should be standing on, in the column on the sprite's right edge)
                    ty = int( ( self.get_y() + self.height - 1 ) / TILE_HEIGHT ) + 1

                    # Check tile walkability
                    if ( not self.can_walk_over_tile(tx1, ty, m) ):

                        # We can not cross any farther than the drop point; we must adjust the entity location to the column we skipped a little ways past
                        self.x = (tx1 * TILE_WIDTH)


                # Check for entity collisions first
                entities = m.master_plane.query_interentity_collision_for_entity_against_entity_types( self.colliding_entity_types_during_movement, self ).filter_out_by_excepting_entity_on_map(self, m, determined, X_AXIS).get_results()

                # We probably can't do this if we're hitting another entity...
                if ( len(entities) > 0 ):

                    # Send touch event to each entity
                    for entity in entities:

                        # Handle touch
                        entity.handle_entity_touch(self, control_center = None, universe = universe) # ?


                    # Correct as far as we need to, to avoid overlapping any colliding entity
                    self.x = self.get_entity_list_min_x(entities) - self.width


                    # An enemy that bumps into someone will eventually prefer to turn around; we achieve this
                    # by pretending his last attempted lateral move went the other way...
                    if (self.genus == GENUS_ENEMY):

                        # Losing patience
                        self.ai_state.ai_patience -= 1

                        # Got no time for this, man!
                        if (self.ai_state.ai_patience <= 0):

                            # Prepare for next time
                            self.ai_state.ai_patience = AI_MAX_PATIENCE

                            # This will force AI characters to try to find another path
                            self.ai_state.last_attempted_lateral_move = DIR_LEFT

                    # Move failed (at least in part)
                    return False

                # If we didn't hit another entity, restore patience...
                else:
                    self.ai_state.ai_patience = AI_MAX_PATIENCE


                if ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    # If we hit a wall... did that wall have spikes?
                    if ( m.master_plane.check_deadly_collision_in_rect_from_direction( self.get_rect(), DIR_RIGHT ) ):

                        # Go ahead and correct the x value...
                        self.x = int(self.get_x() / TILE_WIDTH) * TILE_WIDTH

                        # Entity must die...
                        self.queue_death_by_cause(DEATH_BY_DEADLY_TILE)

                    # If not, handle logic normally...
                    else:

                        # Go ahead and correct the x value...
                        self.x = int(self.get_x() / TILE_WIDTH) * TILE_WIDTH


                    # Move (kind of) failed
                    return False


                # If we made it this far, we know we made a successful move
                self.ai_state.last_lateral_move = DIR_RIGHT

                # Update new direction
                self.set_direction(DIR_RIGHT)

                # Animate sprite
                self.animate()


                # Success!
                return True


    # Move the entity irregardless of whether they're on the ladder, on the ground, etc.
    # Planar shifts use this function when applying friction and such.
    def nudge(self, dx, dy, m):

        if (dy != 0):

            if (dy < 0):

                u = self.y
                self.y += dy

                entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, Y_AXIS).get_results()

                # We probably can't do this if we're hitting another entity...
                if ( len(entities) > 0 ):

                    self.y = self.get_entity_list_max_y(entities)

                    return False


                elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    self.y = int( (self.get_y() / TILE_HEIGHT) + 1) * TILE_HEIGHT

                    return False

                else:

                    return True

            elif (dy > 0):

                self.y += dy

                entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, Y_AXIS).get_results()

                # We probably can't do this if we're hitting another entity...
                if ( len(entities) > 0 ):

                    self.y = self.get_entity_list_min_y(entities) - self.height

                    return False

                elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    self.y = int(self.get_y() / TILE_HEIGHT) * TILE_HEIGHT

                    return False

                else:

                    return True


        elif (dx != 0):

            if (dx < 0):

                self.x += dx

                entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, X_AXIS).get_results()

                # We probably can't do this if we're hitting another entity...
                if ( len(entities) > 0 ):

                    self.x = self.get_entity_list_max_x(entities)

                    return False

                elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    log( self.get_rect() )

                    self.x = int( (self.get_x() / TILE_WIDTH) + 1) * TILE_WIDTH

                    return False

                else:

                    return True

            elif (dx > 0):

                self.x += dx

                entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, X_AXIS).get_results()

                # We probably can't do this if we're hitting another entity...
                if ( len(entities) > 0 ):

                    self.x = self.get_entity_list_min_x(entities) - self.width

                    return False

                elif ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                    self.x = int(self.get_x() / TILE_WIDTH) * TILE_WIDTH

                    return False

                else:

                    return True


    def cascade_to_position(self, x, y, cascade_direction, m):

        if (cascade_direction == DIR_LEFT):

            # Zap new position
            self.x = x - self.width


            # Now the entity must check all other entities to see if they need to cascade away...
            entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, X_AXIS).get_results()

            # Move any* entity we intersect...
            for entity in entities:

                # We must do the same cascade on the intersecting entity...
                entity.cascade_to_position(self.get_x(), None, DIR_LEFT, m)


            # Now we need to see if the entity is colliding with the master plane.  If so, we're going to have
            # to squish the entity.
            if ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                # Since we know which direction we got pushed, the calculation for repositioning and squishing is straightforward...
                squish_amount = TILE_WIDTH - (self.get_x() % TILE_WIDTH)

                self.x = self.get_x() + squish_amount
                self.width -= squish_amount


        elif (cascade_direction == DIR_RIGHT):

            # Zap new position
            self.x = x


            # Now the entity must check all other entities to see if they need to cascade away...
            entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, X_AXIS).get_results()

            # Move any* entity we intersect...
            for entity in entities:

                # We must do the same cascade on the intersecting entity...
                entity.cascade_to_position(self.get_x() + self.width, None, DIR_RIGHT, m)


            # Now we need to see if the entity is colliding with the master plane.  If so, we're going to have
            # to squish the entity.
            if ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                # Since we know which direction we got pushed, the calculation for repositioning and squishing is straightforward...
                squish_amount = (self.get_x() + self.width) % TILE_WIDTH

                self.x = self.get_x()# + squish_amount
                self.width -= squish_amount


        elif (cascade_direction == DIR_UP):

            # Zap new position
            self.y = y - self.height


            # Now the entity must check all other entities to see if they need to cascade away...
            entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, Y_AXIS).get_results()

            # Move any* entity we intersect...
            for entity in entities:

                # We must do the same cascade on the intersecting entity...
                entity.cascade_to_position(None, self.get_y(), DIR_UP, m)


            # Now we need to see if the entity is colliding with the master plane.  If so, we're going to have
            # to squish the entity.
            if ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                # Since we know which direction we got pushed, the calculation for repositioning and squishing is straightforward...
                squish_amount = TILE_HEIGHT - (self.get_y() % TILE_HEIGHT)

                self.y = self.get_y() + squish_amount
                self.height -= squish_amount


        elif (cascade_direction == DIR_DOWN):

            # Zap new position
            self.y = y


            # Now the entity must check all other entities to see if they need to cascade away...
            entities = m.master_plane.query_interentity_collision_for_entity(self).filter_out_by_excepting_entity_on_map(self, m, NOT_DETERMINED, Y_AXIS).get_results()

            # Move any* entity we intersect...
            for entity in entities:

                # We must do the same cascade on the intersecting entity...
                entity.cascade_to_position(None, self.get_y() + self.height, DIR_DOWN, m)


            # Now we need to see if the entity is colliding with the master plane.  If so, we're going to have
            # to squish the entity.
            if ( m.master_plane.check_collision_in_rect( self.get_rect() ) ):

                # Since we know which direction we got pushed, the calculation for repositioning and squishing is straightforward...
                squish_amount = (self.get_y() + self.height) % TILE_HEIGHT

                self.y = self.get_y()# + squish_amount
                self.height -= squish_amount


    # Seek some location (x, y) at the velocity of (vx, vy) on some map m
    def seek_location(self, x, y, vx, vy, universe, recursive = False):

        # Debug testing???
        if (recursive):
            return False


        # When on the same level, simply travel toward the position...
        if (self.get_y() == y):

            # Round y
            self.y = y


            if (self.get_x() < x):

                result = self.move(vx, 0, universe, determined = VERY_DETERMINED, recursive = recursive)

                # Don't overshoot
                if (self.x >= x):

                    # Clamp
                    self.x = x

                # Return move status
                return result


            elif (self.get_x() > x):

                result = self.move(-vx, 0, universe, determined = VERY_DETERMINED, recursive = recursive)

                # Don't overshoot
                if (self.x <= x):

                    # Clamp
                    self.x = x

                # Return move status
                return result


            # We're already at that location
            else:

                # "Reached" location
                return True


        # When lower than the target, the enemy will want to try to find a ladder to climb...
        elif (self.get_y() > y):

            # Fetch the active map
            m = universe.get_active_map()

            # First determine the area in which we could reasonably find a ladder
            (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y())

            ty1 = int(self.get_y() / TILE_HEIGHT)
            ty2 = int( (self.get_y() + (TILE_HEIGHT - 1)) / TILE_HEIGHT)

            # Within those bounds, let's see if we can find a ladder.  if so, we'll want the nearest one...
            shortest_dx = INFINITY

            x_target_ladder = None

            # When having last moved left, we'd prefer a ladder on the left...
            if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):

                for tx in range(tx1, int(self.get_x() / TILE_WIDTH) + 1):

                    # Try to climb a ladder...
                    if ( m.master_plane.check_collision(tx, ty1) == COLLISION_LADDER ):

                        # Make sure there's room to move up...
                        if (
                            ( m.master_plane.check_collision(tx, ty1 - 1) in (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR) ) or
                            self.genus == GENUS_PLAYER
                        ):

                            dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                            if (dx < shortest_dx):
                                shortest_dx = dx

                                # Remember this as our target
                                x_target_ladder = (tx * TILE_WIDTH)

                    # Try to finish climbing the final "rung" of a ladder?
                    elif ( m.master_plane.check_collision(tx, ty2) == COLLISION_LADDER ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):
                            shortest_dx = dx

                            # Remember this as our target
                            x_target_ladder = (tx * TILE_WIDTH)


            # Vice-versa...
            elif (self.ai_state.last_attempted_lateral_move == DIR_RIGHT):

                for tx in range( int(self.get_x() / TILE_WIDTH), tx2):

                    if ( m.master_plane.check_collision(tx, ty1) == COLLISION_LADDER ):

                        # Make sure there's room to move up...
                        if (
                            ( m.master_plane.check_collision(tx, ty1 - 1) in (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR) ) or
                            self.genus == GENUS_PLAYER
                        ):

                            dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                            if (dx < shortest_dx):
                                shortest_dx = dx

                                # Remember this as our target
                                x_target_ladder = (tx * TILE_WIDTH)

                    # Try to finish climbing final "rung"
                    elif ( m.master_plane.check_collision(tx, ty2) == COLLISION_LADDER ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):
                            shortest_dx = dx

                            # Remember this as our target
                            x_target_ladder = (tx * TILE_WIDTH)


            # If we didn't find a ladder in the preferred direction, we'll consider any ladder..
            if (x_target_ladder == None):

                for tx in range(tx1, tx2):

                    if ( m.master_plane.check_collision(tx, ty1) == COLLISION_LADDER ):

                        # Make sure there's room to move up...
                        if (
                            ( m.master_plane.check_collision(tx, ty1 - 1) in (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR) ) or
                            self.genus == GENUS_PLAYER
                        ):

                            dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                            # We'll take the closest ladder.  If there is a tie (one of equal distance in both directions),
                            # we'll take the one on the left unless the destination is to our right.
                            #
                            # This tiebreaker only applies if the enemy doesn't have a memory of its last attempted lateral move...
                            if ( (dx < shortest_dx) or (dx == shortest_dx and (self.get_x() < x)) ):
                                shortest_dx = dx

                                # Remember this as our target
                                x_target_ladder = (tx * TILE_WIDTH)

                    # Finish climbing the final "rung"
                    elif ( m.master_plane.check_collision(tx, ty2) == COLLISION_LADDER ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):
                            shortest_dx = dx

                            # Remember this as our target
                            x_target_ladder = (tx * TILE_WIDTH)


            # If we found a ladder, let's head in its direction...
            if (x_target_ladder != None):

                # Time to climb?
                if (self.get_x() == x_target_ladder):

                    # Perfect alignment
                    self.x = x_target_ladder

                    result = self.move(0, -vy, universe, determined = VERY_DETERMINED, recursive = recursive)

                    # As we're climbing a ladder, we're going to "forget" our last attempted lateral move
                    # so that we can judge the next ladder to climb without bias
                    self.ai_state.last_attempted_lateral_move = DIR_NONE

                    # Don't overshoot
                    if (self.y < y):
                        self.y = y

                    # Return move status
                    return result


                # Not yet; let's get to the ladder first.
                elif (self.get_x() > x_target_ladder):

                    result = self.move(-vx, 0, universe, determined = VERY_DETERMINED, recursive = recursive)

                    # Don't overshoot
                    if (self.x < x_target_ladder):
                        self.x = x_target_ladder

                    # Return move status
                    return result

                elif (self.get_x() < x_target_ladder):

                    result = self.move(vx, 0, universe, determined = VERY_DETERMINED, recursive = recursive)

                    # Don't overshoot
                    if (self.x > x_target_ladder):
                        self.x = x_target_ladder

                    # Return move status
                    return result


            # If we can't find a ladder, let's look for a drop point.  The enemy doesn't care about
            # ladders that go down; if he even found one, then he'd just go right back up that same ladder
            # like a moron.
            else:

                # Find the range
                (cx1, cx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y(), allow_fall = True)
                ty = int(self.get_y() / TILE_HEIGHT)

                shorter_dx = INFINITY
                x_target = None

                # Get the drop points...
                (tx1, tx2) = m.master_plane.get_drop_points_in_tile_coords(self.get_x(), self.get_y())


                # Remember distances, if available...
                dx1 = None
                dx2 = None

                # Left drop point available?
                if (tx1 != None):

                    if (tx1 > cx1):

                        dx1 = abs( (self.get_x() + (self.width / 2)) - ( (tx1 * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx1 < shorter_dx):
                            shorter_dx = dx1

                            # Remember target
                            x_target = (tx1 * TILE_WIDTH)

                # Right drop point available?
                if (tx2 != None):

                    if (tx2 < cx2):

                        dx2 = abs( (self.get_x() + (self.width / 2)) - ( (tx2 * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx2 < shorter_dx):
                            shorter_dx = dx2

                            # Remember target
                            x_target = (tx2 * TILE_WIDTH)


                # We'd really prefer to move in the last direction.  If it's anything close to a tie...
                if ( (dx1 != None) and (dx2 != None) ):

                    # Within 2 tiles of a tie...
                    if ( abs(dx1 - dx2) <= (2 * TILE_WIDTH) ):

                        # If we had been going left, let's stay the course
                        if (self.ai_state.last_attempted_lateral_move == DIR_LEFT):
                            x_target = (tx1 * TILE_WIDTH)

                        # Or right...
                        elif (self.ai_state.last_attempted_lateral_move == DIR_RIGHT):
                            x_target = (tx2 * TILE_WIDTH)


                if (x_target != None):

                    # Time to descend?
                    if (self.get_x() == x_target):

                        # Perfect alignment
                        self.x = x_target

                        result = self.move(0, vy, universe, determined = NOT_DETERMINED, recursive = recursive)

                        # Don't overshoot
                        if (self.y < y):
                            self.y = y

                        # Return move status
                        return result


                    # No!; let's move to the descent point...
                    elif (self.get_x() > x_target):

                        result = self.move(-vx, 0, universe, determined = NOT_DETERMINED, recursive = recursive)

                        # Don't overshoot
                        if (self.x < x_target):
                            self.x = x_target

                        # Return move status
                        return result

                    elif (self.get_x() < x_target):

                        result = self.move(vx, 0, universe, determined = NOT_DETERMINED, recursive = recursive)

                        # Don't overshoot
                        if (self.x > x_target):
                            self.x = x_target

                        # Return move status
                        return result

                else:
                    #print "I can't find a ladder :("
                    pass



        # When higher than the target, let's find the fastest way down...
        elif (self.get_y() < y):

            # Fetch the active map
            m = universe.get_active_map()

            # First determine the area in which we could reasonably find a drop point
            (cx1, cx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y(), allow_fall = True)
            ty = int(self.get_y() / TILE_HEIGHT)

            # Within those bounds, let's see if we can find a ladder down, or a drop point.  if so, we'll want the nearest option...
            shortest_dx = INFINITY


            # We'll have to check for both ladders and drop points...
            x_target_any = None


            # Let's look at ladders first...
            for tx in range(cx1, cx2):

                if ( m.master_plane.check_collision(tx, ty + 1) == COLLISION_LADDER ):

                    dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                    if (dx < shortest_dx):

                        shortest_dx = dx

                        # Remember this as the target
                        x_target_any = (tx * TILE_WIDTH)

                    elif ( (dx == shortest_dx) and (self.ai_state.last_lateral_move == DIR_RIGHT) ):

                        x_target_any = (tx * TILE_WIDTH)


            # Now let's look at the drop points...
            (tx1, tx2) = m.master_plane.get_drop_points_in_tile_coords(self.get_x(), self.get_y())


            # Left drop point available?
            if (tx1 != None):

                if (tx1 > cx1):

                    dx = abs( (self.get_x() + (self.width / 2)) - ( (tx1 * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                    if (dx < shortest_dx):
                        shortest_dx = dx

                        # Remember target
                        x_target_any = (tx1 * TILE_WIDTH)

            # Right drop point available?
            if (tx2 != None):

                if (tx2 < cx2):

                    dx = abs( (self.get_x() + (self.width / 2)) - ( (tx2 * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                    if (dx < shortest_dx):

                        shortest_dx = dx

                        # Remember target
                        x_target_any = (tx2 * TILE_WIDTH)

                    elif ( (dx == shortest_dx) and (self.ai_state.last_lateral_move == DIR_RIGHT) ):

                        ##x_target_any = (tx * TILE_WIDTH)
                        x_target_any = (tx2 * TILE_WIDTH)


            # Did we find a target?
            if (x_target_any != None):

                # Time to descend?
                if (self.get_x() == x_target_any):

                    # Perfect alignment
                    self.x = x_target_any

                    result = self.move(0, vy, universe, determined = VERY_DETERMINED, recursive = recursive)

                    # Don't overshoot
                    if (self.y > y):
                        self.y = y

                    # Return move status
                    return result

                # No!; let's move to the descent point...
                elif (self.get_x() > x_target_any):

                    #print "move left @ ", -(self.speed + self.sprint_bonus)
                    result = self.move(-vx, 0, universe, determined = VERY_DETERMINED, recursive = recursive)

                    # Don't overshoot
                    if (self.x < x_target_any):
                        self.x = x_target_any

                    # Return move status
                    return result

                elif (self.get_x() < x_target_any):

                    result = self.move(vx, 0, universe, determined = VERY_DETERMINED, recursive = recursive)

                    # Don't overshoot
                    if (self.x > x_target_any):
                        self.x = x_target_any

                    # Return move status
                    return result

            else:
                #print "I'm not sure where to descend..."
                ##pass
                return False


    # Avoid some location (x, y) at the velocity of (vx, vy) on some map m
    def avoid_location(self, x, y, vx, vy, universe, recursive = False):

        # Get the active map
        m = universe.get_active_map()

        # When on the same level, we must run away from the location.  We want the first ladder or drop point we can possibly find...
        if (self.get_y() == y):

            # Perfect alignment
            self.y = y


            # We'll take whatever is closest...
            x_target_ladder = None
            x_target_drop = None


            # Check for a ladder on the left of the avoid location...
            if (self.get_x() < x):

                # Determine choke points
                (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y())

                # Definitely don't walk toward the location when on the same y-axis level...
                tx2 = int(self.get_x() / TILE_WIDTH) + 1


                ty1 = int(self.get_y() / TILE_HEIGHT)
                ty2 = int( (self.get_y() + (TILE_HEIGHT - 1)) / TILE_HEIGHT)


                # Find the nearest ladder / drop point in the possible range...
                shortest_dx = INFINITY

                for tx in range(tx1, tx2):

                    # Check for a ladder...
                    if ( m.master_plane.check_collision(tx, ty1) == COLLISION_LADDER ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):

                            shortest_dx = dx

                            x_target_ladder = (tx * TILE_WIDTH)
                            x_target_drop = None

                    # Check for drop points
                    elif ( m.master_plane.check_faux_collision(tx, ty1 + 1) in (COLLISION_LADDER, COLLISION_MONKEYBAR, COLLISION_NONE) ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):

                            shortest_dx = dx

                            x_target_drop = (tx * TILE_WIDTH)
                            x_target_ladder = None


                # Did we find a ladder?
                if (x_target_ladder):

                    # Time to climb?
                    if (self.get_x() == x_target_ladder):

                        self.move(0, -vy, universe, recursive = recursive)


                    # No; let's get to the ladder!
                    elif (self.get_x() > x_target_ladder):

                        self.move(-vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x < x_target_ladder):
                            self.x = x_target_ladder

                    elif (self.get_x() < x_target_ladder):

                        self.move(vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x > x_target_ladder):
                            self.x = x_target_ladder

                # Maybe we found a drop point?
                elif (x_target_drop):

                    # In case we're dropping down a ladder...
                    if (self.get_x() == x_target_drop):

                        self.move(0, vy, universe, recursive = recursive)


                    # Run to the drop point
                    elif (self.get_x() > x_target_drop):

                        self.move(-vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x < x_target_drop):
                            self.x = x_target_drop

                    elif (self.get_x() < x_target_drop):

                        self.move(vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x > x_target_drop):
                            self.x = x_target_drop

                # If we didn't find a ladder OR a drop point (dead end), then we just run away...
                else:

                    self.move(-vx, 0, universe, recursive = recursive)

            # >= in case the enemy is standing at "last known position" where the player was standing before invisibility / hologram / whatever...
            elif (self.get_x() >= x):

                # Determine choke points
                (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y())

                # We refuse to go any nearer the location
                tx1 = int(self.get_x() / TILE_WIDTH)


                ty1 = int(self.get_y() / TILE_HEIGHT)
                ty2 = int( (self.get_y() + (TILE_HEIGHT - 1)) / TILE_HEIGHT)


                # Find the nearest ladder / drop point in the possible range...
                shortest_dx = INFINITY

                for tx in range(tx1 - 1, tx2 + 1):

                    # Check for a ladder...
                    if ( m.master_plane.check_collision(tx, ty1) == COLLISION_LADDER ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):

                            shortest_dx = dx

                            x_target_ladder = (tx * TILE_WIDTH)
                            x_target_drop = None

                    # Check for drop points
                    elif ( m.master_plane.check_faux_collision(tx, ty1 + 1) in (COLLISION_LADDER, COLLISION_MONKEYBAR, COLLISION_NONE) ):

                        dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                        if (dx < shortest_dx):

                            shortest_dx = dx

                            x_target_drop = (tx * TILE_WIDTH)
                            x_target_ladder = None


                # Did we find a ladder?
                if (x_target_ladder):

                    # Time to climb?
                    if (self.get_x() == x_target_ladder):

                        self.move(0, -vy, universe, recursive = recursive)


                    # No; let's get to the ladder!
                    elif (self.get_x() > x_target_ladder):

                        self.move(-vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x < x_target_ladder):
                            self.x = x_target_ladder

                    elif (self.get_x() < x_target_ladder):

                        self.move(vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x > x_target_ladder):
                            self.x = x_target_ladder

                # Maybe we found a drop point?
                elif (x_target_drop):

                    # In case we're dropping down a ladder...
                    if (self.get_x() == x_target_drop):

                        self.move(0, vy, universe, recursive = recursive)


                    # Run to the drop point
                    elif (self.get_x() > x_target_drop):

                        self.move(-vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x < x_target_drop):
                            self.x = x_target_drop

                    elif (self.get_x() < x_target_drop):

                        self.move(vx, 0, universe, recursive = recursive)

                        # Don't overshoot
                        if (self.x > x_target_drop):
                            self.x = x_target_drop

                # If we didn't find a ladder OR a drop point (dead end), then we just run away...
                else:

                    self.move(vx, 0, universe, recursive = recursive)


        # When lower than the target, we'll try to get even lower...
        elif (self.get_y() > y):

            # First determine the area in which we could reasonably find a ladder
            (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y())

            ty1 = int(self.get_y() / TILE_HEIGHT)
            ty2 = int( (self.get_y() + (TILE_HEIGHT - 1)) / TILE_HEIGHT)


            # Definitely don't walk toward the location...
            if (self.get_x() < x):
                tx2 = int(self.get_x() / TILE_WIDTH) + 1

            elif (self.get_x() > x):
                tx1 = int(self.get_x() / TILE_WIDTH)


            # Within those bounds, let's see if we can find a ladder.  if so, we'll want the nearest one...
            shortest_dx = INFINITY

            x_target_ladder = None
            x_target_drop = None



            # No "preferred direction" nonsense.  The enemy is freaked out, and he's stupid.  He's going to get down as quickly as possible.
            shortest_dx = INFINITY

            for tx in range(tx1 - 1, tx2 + 1):

                # Check for a ladder...
                if ( m.master_plane.check_collision(tx, ty1 + 1) == COLLISION_LADDER ):

                    dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                    if (dx < shortest_dx):

                        shortest_dx = dx

                        x_target_ladder = (tx * TILE_WIDTH)
                        x_target_drop = None

                # Check for drop points
                elif ( m.master_plane.check_collision(tx, ty1 + 1) in (COLLISION_LADDER, COLLISION_MONKEYBAR, COLLISION_NONE) ):

                    dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                    if (dx < shortest_dx):

                        shortest_dx = dx

                        x_target_drop = (tx * TILE_WIDTH)
                        x_target_ladder = None



            # Did we find a ladder?
            if (x_target_ladder):

                # Time to descend?
                if (self.get_x() == x_target_ladder):

                    self.move(0, vy, universe, recursive = recursive)


                # No; let's get to the ladder!
                elif (self.get_x() > x_target_ladder):

                    self.move(-vx, 0, universe, recursive = recursive)

                    # Don't overshoot
                    if (self.x < x_target_ladder):
                        self.x = x_target_ladder

                elif (self.get_x() < x_target_ladder):

                    self.move(vx, 0, universe, recursive = recursive)

                    # Don't overshoot
                    if (self.x > x_target_ladder):
                        self.x = x_target_ladder

            # Maybe we found a drop point?
            elif (x_target_drop):

                if (self.get_x() == x_target_drop):

                    self.move(0, vy, universe, recursive = recursive)


                # Run to the drop point
                elif (self.get_x() > x_target_drop):

                    self.move(-vx, 0, universe, recursive = recursive)

                    # Don't overshoot
                    if (self.x < x_target_drop):
                        self.x = x_target_drop

                elif (self.get_x() < x_target_drop):

                    self.move(vx, 0, universe, recursive = recursive)

                    # Don't overshoot
                    if (self.x > x_target_drop):
                        self.x = x_target_drop

            # If we didn't find a ladder OR a drop point (dead end), then we just run away...
            else:

                if (self.get_x() < x):
                    self.move(-vx, 0, universe, recursive = recursive)

                else:
                    self.move(vx, 0, universe, recursive = recursive)


        # When higher than the target, let's find the fastest way up...
        elif (self.get_y() < y):

            # First determine the area in which we could reasonably find a ladder
            (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y())

            ty1 = int(self.get_y() / TILE_HEIGHT)
            ty2 = int( (self.get_y() + (TILE_HEIGHT - 1)) / TILE_HEIGHT)


            # Definitely don't walk toward the location...
            if (self.get_x() < x):
                tx2 = int(self.get_x() / TILE_WIDTH) + 1

            elif (self.get_x() > x):
                tx1 = int(self.get_x() / TILE_WIDTH)


            # Within those bounds, let's see if we can find a ladder.  if so, we'll want the nearest one...
            shortest_dx = INFINITY

            x_target_ladder = None


            # No "preferred direction" nonsense.  The enemy is freaked out, and he's stupid.  He's going to climb as quickly as possible.
            shortest_dx = INFINITY

            for tx in range(tx1, tx2):

                # Check for a ladder...
                if ( m.master_plane.check_collision(tx, ty1) == COLLISION_LADDER ):

                    dx = abs( (self.get_x() + (self.width / 2)) - ( (tx * TILE_WIDTH) + (TILE_WIDTH / 2) ) )

                    if (dx < shortest_dx):

                        shortest_dx = dx

                        x_target_ladder = (tx * TILE_WIDTH)


            # Did we find a ladder?
            if (x_target_ladder):

                # Time to climb?
                if (self.get_x() == x_target_ladder):

                    self.move(0, -vy, universe, recursive = recursive)


                # No; let's get to the ladder!
                elif (self.get_x() > x_target_ladder):

                    self.move(-vx, 0, universe, recursive = recursive)

                    # Don't overshoot
                    if (self.x < x_target_ladder):
                        self.x = x_target_ladder

                elif (self.get_x() < x_target_ladder):

                    self.move(vx, 0, universe, recursive = recursive)

                    # Don't overshoot
                    if (self.x > x_target_ladder):
                        self.x = x_target_ladder

            # If we didn't find a ladder, then we just run away...
            else:

                if (self.get_x() < x):
                    self.move(-vx, 0, universe, recursive = recursive)

                else:
                    self.move(vx, 0, universe, recursive = recursive)


    def get_entity_list_min_x(self, entities):

        x = INFINITY

        for entity in entities:

            if (not (self == entity.ai_state.ai_frozen_for)):
                if (entity.get_x() < x):
                    x = entity.get_x()

            #else:
            #    log( "\t\tHe is frozen, for me..." )

            #if (entity.genus == GENUS_PLAYER):
            #    log( 5/0 )

        if (x == INFINITY):
            x = 0

        return x

    def get_entity_list_min_y(self, entities):

        y = INFINITY

        for entity in entities:

            if (not (self == entity.ai_state.ai_frozen_for)):
                if (entity.get_y() < y):
                    y = entity.get_y()

        return y

    def get_entity_list_max_x(self, entities):

        x = -INFINITY

        for entity in entities:

            if (not (self == entity.ai_state.ai_frozen_for)):
                if ( (entity.get_x() + entity.width) > x):
                    x = (entity.get_x() + entity.width)

            #if (entity.genus == GENUS_PLAYER):
            #    log( 5/0 )

        if (x == -INFINITY):
            x = 0

        return x

    def get_entity_list_max_y(self, entities):

        y = -INFINITY

        for entity in entities:

            if (not (self == entity.ai_state.ai_frozen_for)):
                if ( (entity.get_y() + entity.height) > y):
                    y = (entity.get_y() + entity.height)

        return y

    # Check a given tile to see if this entity recently escaped from a dig trap at that
    # position.  If so, the entity can "walk" on that location for a short duration.
    def can_find_escaped_dig_trap(self, tx, ty, m):

        # Only enemies can do this
        if ( not (self.genus in (GENUS_ENEMY,)) ):

            return False

        else:

            # Does the enemy have a trap exception at the given location?
            return ( self.ai_state.ai_trap_exception == (tx, ty) )


    def check_for_dig_trap(self, x, y, universe):

        if ( not (self.genus in (GENUS_ENEMY,)) ):
            return False


        # Only bother when at an exact row...
        if ( int(y) % TILE_HEIGHT > 0):
            return False

        # Also, if we're already trapped, well...
        elif (self.ai_state.ai_is_trapped):
            return False


        # Fetch the active map
        m = universe.get_active_map()


        (tx, ty) = (
            (x / TILE_WIDTH),
            (y / TILE_HEIGHT)
        )

        #print "checking for trap at %d, %d" % (tx, ty)

        if ( m.trap_exists_at_tile_coords(tx, ty, self.ai_state.ai_trap_exception) ):

            # Perfect alignment
            self.x = (tx * TILE_WIDTH)
            self.y = (ty - 1) * TILE_HEIGHT

            # Set us as trapped
            self.ai_state.ai_is_trapped = True


            # Sometimes the player's inventory can affect for how long enemies will remain trapped
            modifier = (
                1.0 +
                sum( o.attributes["enemy-trapped-length-bonus"] for o in universe.equipped_inventory )
            )

            #bonus = random.randint(1, 200)
            #log2( "bonus for '%s': %s" % (self.name, bonus) )

            # Set how long the enemy will remain trapped for.  Hack in a sane minimum of 1 (hard-coded)
            self.ai_state.ai_trap_time_remaining = int(modifier * AI_MAX_TRAP_TIME)
            #self.ai_state.ai_trap_time_remaining += bonus #debug hard-coded

            # Remember the location as the trap exception for when we climb out...
            self.ai_state.ai_trap_exception = (tx, ty)
            self.ai_state.ai_trap_exception_time = AI_MAX_TRAP_EXCEPTION_TIME


            # Drop any gold we might have been carrying
            if (self.ai_state.ai_is_carrying_gold):

                #self.drop_gold_at_tile_coords(tx, ty - 1, m)
                self.queue_gold_drop_at_location(tx, ty - 1)


    def queue_gold_drop_at_location(self, tx, ty):

        self.queued_gold_drop_location = (tx, ty)


    def drop_gold_at_tile_coords(self, gold, tx, ty, control_center, universe):#network_controller, universe, p_map):

        # Fetch network controller
        network_controller = control_center.get_network_controller()


        # During netplay, the client's enemies do not directly drop the gold; the client relies
        # on the server for gold sync information.
        if ( network_controller.get_status() != NET_STATUS_CLIENT ):

            self.ai_state.ai_is_carrying_gold = False
            self.ai_state.ai_is_carrying_gold_by_name = ""

            # Position the gold immediately above the trap and set it to active
            gold.x = (tx * TILE_WIDTH)
            gold.y = ( (ty) * TILE_HEIGHT)

            gold.queue_for_reactivation()


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        # Active hologram?
        if (self.status == STATUS_ACTIVE):

            # Fetch active map
            m = universe.get_active_map()

            # Do hologram gravity
            self.do_gravity(RATE_OF_GRAVITY, universe)


    # Overwrite as necessary
    def process_drama(self, control_center, universe):

        # Process particles
        for particle in self.particles:
            particle.process(None)

    #def post_process(self, p_map, session = None):
    def post_process(self, control_center, universe):#network_controller, universe, p_map, session):

        # Remove lost particles
        i = 0

        while (i < len(self.particles)):

            if (self.particles[i].state == False):
                self.particles.pop(i)

            else:
                i += 1


    # Set entity direction
    def set_direction(self, direction):

        # Don't "redundantly" set direction, as setting direction resets frame animation data
        if (self.direction != direction):

            # Set direction
            self.direction = direction

            # Reset to first frame
            self.frame = 0
            self.frame_interval = self.frame_delay


    # Get entity direction
    def get_direction(self):

        # Return
        return self.direction


    # Overwrite this in inheriting classes
    def animate(self):

        return


    # By default, entities do not support fade.  Overwrite where needed.
    def fade_in(self):

        # Assume fully faded in, "success"
        return True


    # Default
    def fade_out(self):

        # Assume success
        return True


    def render(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        if (self.status == STATUS_ACTIVE):

            if ( (is_editor) or (not self.editor_only) ):

                window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, gl_color = gl_color)


    # By default, render_scaled just uses the ordinary render function.
    # This is really just temporary until I copy this function into each entity type...
    def render_scaled(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        # Assumed rendering point
        (rx, ry) = (
            0 + int( scale * self.get_x() ),
            0 + int( scale * self.get_y() )
        )

        # True scaled rectangle
        rScaled = self.get_scaled_rect(scale = scale)

        # The point where we really want to render to account for tile width / height rounding
        (adjustedX, adjustedY) = (
            rScaled[0],
            rScaled[1]
        )

        # Render as usual, but account for the rounding differential on each axis
        self.render(sx + (adjustedX - rx), sy + (adjustedY - ry), sprite, scale, is_editor, gl_color, window_controller = window_controller)


# This entity extension allows an Entity-based class to
# import an "explode" method that allows the object to explode.
class ExplodingEntityExt:

    def __init__(self):

        # Nothing to set up; we're just installing the .explode method.
        pass


    def explode(self, corpse = False, radius = 1, control_center = None, universe = None):

        # Disable rendering / processing
        self.alive = False

        self.set_status(STATUS_INACTIVE)

        # Should the entity corpse?  Bombs will always corpse; other entities, such as enemies... they probably won't.
        self.corpsed = corpse


        # Fetch active map
        m = universe.get_active_map()


        # Shake the screen for a moment
        if (radius == 1):
            m.requested_shake_tuple = (SHAKE_WEAK, SHAKE_BRIEFLY)

        # Powerful bombs will shake the screen more crazily
        else:
            m.requested_shake_tuple = (SHAKE_STRONG, SHAKE_BRIEFLY)


        # Create a few colorcles
        (cx, cy) = (
            self.get_x() + int(self.width / 2),
            self.get_y() + int(self.height / 2)
        )

        for i in range(0, 25):

            m.colorcles.append(
                Colorcle(cx + random.randint(-8, 8), cy + random.randint(-8, 8), (220, 110, 0, 0.75), (50, 50, 0))
            )


        # Dig all surrounding tiles...
        (tx, ty) = (
            int(self.get_x() / TILE_WIDTH),
            int(self.get_y() / TILE_HEIGHT)
        )

        for y in range(ty - radius, ty + radius + 1):

            for x in range(tx - radius, tx + radius + 1):

                # Emulate a scripted dig; scripted digs can dig any tile...
                m.dig_tile_at_tile_coords(x, y, scripted_dig = True)#True)


        # Destroy any nearby entity.  First define the rectangle at the center of the bomb; we'll shift it in a moment...
        rBomb = (self.get_x() + int(self.width / 2), self.get_y() + int(self.height / 2), (1 + (2 * radius)) * TILE_WIDTH, (1 + (2 * radius)) * TILE_HEIGHT)

        # Now, offset that rect to center on the bomb
        rBomb = offset_rect(rBomb, x = -1 * int(rBomb[2] / 2), y = -1 * int(rBomb[3] / 2))


        # Count how many bad guys we're destroying wtih this bomb
        bad_guys_killed = 0

        # Destroy any nearby entity on the active map...
        for entity in m.get_bombable_entities():

            # Don't test against ourself, no matter what!
            if ( not (entity == self) ):

                # Check intersection
                if ( intersect(rBomb, entity.get_rect()) ):

                    # Queue death
                    entity.queue_death_by_cause(DEATH_BY_BOMB)

                    # Is this entity a bad guy?
                    if (entity.genus == GENUS_ENEMY):

                        # Count another bad guy hit
                        bad_guys_killed += 1

                        # Execute the appropriate killed bad guy(s) achievement hook(s).
                        # Note that if we get more than 1 with this bomb, we'll call the hook for each step (x1, x2, etc.)
                        universe.execute_achievement_hook( "killed-bad-guy-x%d" % bad_guys_killed, control_center )


        # Bomb exploding sound effect
        control_center.get_sound_controller().queue_sound(SFX_BOMB_EXPLODE)


# Players and (sometimes) Holograms will have the ability to permanently "collect" gold.
# Enemies, though, will NOT use this extension; they can pick up gold, but they cannot "collect" it.
# "Collecting" gold adds to the player's gold count and marks the gold bar as permanently collected!
class GoldCollectorEntityExt:

    def __init__(self):

        # Nothing to do here...
        pass

    #def check_for_gold_collection(self, universe, p_map, session):
    def fetch_first_touched_gold(self, control_center, universe):#network_controller, universe, p_map, session):

        # Fetch network controller
        network_controller = control_center.get_network_controller()


        # During netplay, the client cannot register gold collection at all.  The server will keep them updated via net messages...
        if ( network_controller.get_status() == NET_STATUS_CLIENT ):

            return None

        # Otherwise, we'll check the area for any gold...
        else:

            # Fetch active map
            m = universe.get_active_map()

            r = self.get_rect()

            entity_names = m.master_plane.get_gold_in_rect(r)

            for name in entity_names:

                entity = m.get_entity_by_name(name)

                if (entity and (not entity.collected)):

                    if ( intersect(r, entity.get_rect()) ):

                        log2( self.name, "touched", name )
                        # First, mark the gold as collected...
                        #entity.mark_as_collected_by_actor(universe, m, session, actor = self)
                        return entity



class Player(Entity, GoldCollectorEntityExt, UITemplateLoaderExt):

    def __init__(self):

        Entity.__init__(self)
        GoldCollectorEntityExt.__init__(self)
        UITemplateLoaderExt.__init__(self)

        self.genus = GENUS_PLAYER
        self.species = None


        """
        Debug
        """
        # Let's track user input history while debug mode is on
        self.recording = False
        self.recording_data = []
        """
        End Debug
        """


        # At timsi (e.g. during netplay) the player object will have its own unique color.
        # We'll track that when/a with this variable.
        self.queued_avatar_data = None


        # Interentity collision behavior overwrites
        self.colliding_entity_types_during_movement = (GENUS_ENEMY,)
        self.colliding_entity_types_during_gravity = (GENUS_PLAYER, GENUS_ENEMY)


        # Define frame indices
        self.frame_indices = {

            DIR_UP: EntityFrameDatum(
                sequence = range(38, 46)
            ),

            DIR_RIGHT: EntityFrameDatum(
                sequence = range(0, 19)
            ),

            DIR_DOWN: EntityFrameDatum(
                sequence = range(38, 46)
            ),

            DIR_LEFT: EntityFrameDatum(
                sequence = range(0, 19),
                hflip = True
            ),

            DIR_DIG_LEFT: EntityFrameDatum(
                sequence = range(46, 76),
                hflip = True
            ),

            DIR_DIG_RIGHT: EntityFrameDatum(
                sequence = range(46, 76)
            ),

            DIR_SWING_LEFT: EntityFrameDatum(
                sequence = range(19, 38),
                hflip = True
            ),

            DIR_SWING_RIGHT: EntityFrameDatum(
                sequence = range(19, 38)
            ),

        }

        # Override default frame delay
        self.frame_delay = 2

        # Powerup trackers
        self.is_invisible = False


        # Inventory items acquired
        self.inventory = []

        #for i in range(0, 5):
        #    x = InventoryItem()
        #    x.randomize(max_quality = 2)
        #    self.inventory.append(x)

        # Equipped inventory items
        self.active_inventory_indices = []


        # Sometimes the player might get stuck...
        self.suicide_interval = 0
        self.suicide_interval_max = SUICIDE_INTERVAL_MAX

        # Determine how to react to collisions...
        self.food_chain_position = 1


        """ DEBUG """
        #self.speed *= 2
        """ End DEBUG """


    # The Player object doesn't save or load memory data.
    # It either exists, or it's game over.  Player settings
    # are only tracked by the universe's session.
    def save_state(self):

        # Unused
        return XMLNode("player").set_attributes({
            "rel": xml_encode( "session data" )
        })

    # Player object uses session state data
    def load_state(self, node):

        # Do nothing
        return


    # Colorify with semicolon-separated values (overwrite)
    def colorify(self, ssv):

        # Queue it up, basically.  We'll handle this in detail within draw()
        self.queued_avatar_data = ssv


    def get_suicide_interval_percentage(self):

        if (self.suicide_interval > 0):

            return float(self.suicide_interval) / float(self.suicide_interval_max)

        else:

            return 0


    def get_speed(self, universe):

        # Check for cached value
        speed = universe.get_cached_item_attribute_result("player-speed")

        # No cache value?
        if (speed == None):

            # Calculate modifier
            modifier = (
                1.0 +
                sum( o.attributes["gold-pickup-player-speed-bonus"] for o in universe.get_equipped_items() if o.is_active() ) +
                sum( o.attributes["player-speed-modifier"] for o in universe.get_equipped_items() )
            )

            # Calculate final speed
            speed = (modifier * self.speed)

            # Cache new player speed; it will apply until this item's timer expires
            universe.cache_item_attribute_result(
                "player-speed",
                speed
            )

        """
        # Is the player wearing items that make the player go faster/slower?
        inventory_aggregate = sum( o.attributes["player-speed-modifier"] for o in universe.equipped_inventory )

        # Sum
        speed = self.speed + inventory_aggregate
        """

        # This is all we need to do here...
        return speed


    def handle_user_input(self, user_input, control_center, universe):#network_controller, universe, p_map, session):

        """
        Debug
        """
        # Enable/disable recording logic check
        if (False):

            # Should we track recording data?
            if (self.recording):

                # Done with recording mode?
                if (INPUT_DEBUG in user_input):

                    # End recording
                    self.recording = False

                    # Dump data to file base on current map's name
                    f = open( os.path.join( "logs", "%s.animation.txt" % universe.get_active_map().get_name() ), "w" )
                    f.write(
                        "\n".join(self.recording_data)
                    )
                    f.close()

                    logn( "replay debug", "Input Recording:  Off (file saved)" )

                # Continue tracking input history
                else:

                    # Track current frame data
                    self.recording_data.append( ",".join( "%d" % o for o in user_input ) )

            # Check to see if we should start recording
            else:

                # Activate?
                if (INPUT_DEBUG in user_input):

                    # Enable flag
                    self.recording = True

                    # Clear data log
                    self.recording_data = []


                    # Unpause the universe; we pause it at the start of the game when creating these debug recordings.
                    universe.unpause()

                    logn( "replay debug", "Input Recording:  On" )
        """
        End Debug
        """


        # Fetch the network controller;
        network_controller = control_center.get_network_controller()

        # and the sound controller
        sound_controller = control_center.get_sound_controller()


        # Until we can prove otherwise...
        self.moved_this_frame = False


        # Make a quick copy of the previous input
        previous_input_copy = []
        previous_input_copy.extend(self.previous_input)

        # Reset hard copy of previous input
        self.previous_input = []


        if (self.status != STATUS_ACTIVE):
            return

        # Can't do anything while in dig delay...
        if (self.dig_delay > 0):
            return


        # Fetch the active map
        m = universe.get_active_map()

        # Let's also grab the active map's wave tracker
        wave_tracker = m.get_wave_tracker()


        if ( len(self.network_input) > 0 ):
            log( "network_input = ", self.network_input )


        # Check for intentional suicide
        if (INPUT_SUICIDE in user_input):

            self.suicide_interval += 1

            # Game over man?
            if (self.suicide_interval >= self.suicide_interval_max):

                # Cap it
                self.suicide_interval = self.suicide_interval_max

                # Goodbye...
                self.queue_death_by_cause(DEATH_BY_SUICIDE)

        # Reset suicide hold timer if necessary
        else:

            self.suicide_interval = 0


        # If the player can move, check for movement input commands...
        if (self.can_move):

            # How quickly will they seek / flee?
            speed = self.get_speed(universe)

            #print "speed x = %s, speed y = %s, sprint bonus = %s (timer:  %s)" % (speed_x, speed_y, self.sprint_bonus, universe.get_session_variable("core.skills.sprint:timer").get_value())

            if (INPUT_MOVE_LEFT in user_input):

                # Mirror speed for each axis, adjusting for known latency
                (speed_x, speed_y) = self.adjust_speed_for_latency(speed, 0, self.get_x() - 100, 0) # Hack an offset of 100 as a hint to the latency adjustment calculation (directional hint)

                self.moved_this_frame = self.move( -(speed_x + self.sprint_bonus), 0, universe )

                if (self.moved_this_frame):

                    if ( not (INPUT_MOVE_LEFT in previous_input_copy) ):

                        network_controller.send_entity_start_motion(
                            entity = self,
                            direction = DIR_LEFT,
                            control_center = control_center,
                            universe = universe
                        )

                    self.previous_input.append(INPUT_MOVE_LEFT)

                    if (self.footstep_interval == 0):
                        sound_controller.queue_sound(SFX_PLAYER_WALK)

            elif (INPUT_MOVE_RIGHT in user_input):

                # Mirror speed for each axis, adjusting for known latency
                (speed_x, speed_y) = self.adjust_speed_for_latency(speed, 0, self.get_x() + 100, 0) # Hack an offset of 100 as a hint to the latency adjustment calculation (directional hint)

                self.moved_this_frame = self.move( (speed_x + self.sprint_bonus), 0, universe )

                if (self.moved_this_frame):

                    if ( not (INPUT_MOVE_RIGHT in previous_input_copy) ):

                        network_controller.send_entity_start_motion(
                            entity = self,
                            direction = DIR_RIGHT,
                            control_center = control_center,
                            universe = universe
                        )


                    self.previous_input.append(INPUT_MOVE_RIGHT)

                    if (self.footstep_interval == 0):
                        sound_controller.queue_sound(SFX_PLAYER_WALK)

            elif (INPUT_MOVE_UP in user_input):

                # Mirror speed for each axis, adjusting for known latency
                (speed_x, speed_y) = self.adjust_speed_for_latency(0, speed, 0, self.get_y() - 100) # Hack an offset of 100 as a hint to the latency adjustment calculation (directional hint)

                self.moved_this_frame = self.move(0, -speed_y, universe)

                if (self.moved_this_frame):

                    if ( not (INPUT_MOVE_UP in previous_input_copy) ):

                        network_controller.send_entity_start_motion(
                            entity = self,
                            direction = DIR_UP,
                            control_center = control_center,
                            universe = universe
                        )

                    self.previous_input.append(INPUT_MOVE_UP)

            elif (INPUT_MOVE_DOWN in user_input):

                # Mirror speed for each axis, adjusting for known latency
                (speed_x, speed_y) = self.adjust_speed_for_latency(0, speed, 0, self.get_y() + 100) # Hack an offset of 100 as a hint to the latency adjustment calculation (directional hint)

                self.moved_this_frame = self.move(0, speed_y, universe)

                if (self.moved_this_frame):

                    if ( not (INPUT_MOVE_DOWN in previous_input_copy) ):

                        network_controller.send_entity_start_motion(
                            entity = self,
                            direction = DIR_DOWN,
                            control_center = control_center,
                            universe = universe
                        )

                    self.previous_input.append(INPUT_MOVE_DOWN)


            if (INPUT_DIG_LEFT in user_input):

                # Get duration multiplier without cache
                self.dig_to_direction(
                    DIR_LEFT,
                    control_center,
                    universe,
                    depth = 1,
                    duration_multiplier = 1.0 + sum( o.attributes["dig-length-bonus"] for o in universe.get_equipped_items() )
                )

            elif (INPUT_DIG_RIGHT in user_input):

                #self.dig_to_direction(DIR_RIGHT, control_center, universe, distance = 1)
                # Get duration multiplier without cache
                self.dig_to_direction(
                    DIR_RIGHT,
                    control_center,
                    universe,
                    depth = 1,
                    duration_multiplier = 1.0 + sum( o.attributes["dig-length-bonus"] for o in universe.get_equipped_items() )
                )

            elif (INPUT_DIG_FORWARD in user_input):

                # Assume
                dig_direction = None

                # Currently facing left?
                if ( self.get_direction() == DIR_LEFT ):

                    # Try to dig left
                    dig_direction = DIR_LEFT

                # Currently facing right?
                elif ( self.get_direction() == DIR_RIGHT ):

                    # Try to dig right
                    dig_direction = DIR_RIGHT


                # Do we have a direction?
                if (dig_direction != None):

                    # Attempt dig now
                    self.dig_to_direction(
                        dig_direction,
                        control_center,
                        universe,
                        depth = 1,
                        duration_multiplier = 1.0 + sum( o.attributes["dig-length-bonus"] for o in universe.get_equipped_items() )
                    )


            if (INPUT_BOMB in user_input):

                #print wave_tracker.count_free_bombs_remaining()
                #print universe.get_active_map().get_param("type")
                #print int(universe.get_session_variable("core.bombs.count").get_value())
                #print 5/0

                # Unless bombs on this map wave are free of charge, then we need to have at least one bomb.
                # Player bomb "wallet" only works if the player is not in a puzzle/challenge room.  (Otherwise, we depend on the wave allowance.)
                if ( (wave_tracker.count_free_bombs_remaining() >= 1) or ( (not ( universe.get_active_map().get_param("type") in ("puzzle", "challenge") )) and (int(universe.get_session_variable("core.bombs.count").get_value() ) >= 1) ) ):

                    if (self.direction == DIR_LEFT):

                        bomb = self.bomb_to_direction(DIR_LEFT, control_center, universe, radius = 1, remote = ( int( universe.get_session_variable("core.skills.remote-bomb:bombs-remaining").get_value() ) > 0 ) )

                        if (bomb):

                            # Lower bomb count, unless they're free on this map wave...
                            #if ( wave_tracker.get_wave_param("bombs-free") != 1 ):
                            if ( not ( universe.get_active_map().get_param("type") in ("puzzle", "challenge") ) ):

                                # One less bomb
                                universe.increment_session_variable("core.bombs.count", -1)


                            # Always track that we just used a bomb
                            wave_tracker.increment_wave_counter("bombs", 1)

                            # Update map param that tracks bombs used
                            universe.get_active_map().set_param(
                                "stats.bombs-used",
                                1 + universe.get_active_map().get_param("stats.bombs-used")
                            )


                            # Place bomb sound effect
                            control_center.get_sound_controller().queue_sound(SFX_PLACE_BOMB)

                    elif (self.direction == DIR_RIGHT):

                        bomb = self.bomb_to_direction(DIR_RIGHT, control_center, universe, radius = 1, remote = ( int( universe.get_session_variable("core.skills.remote-bomb:bombs-remaining").get_value() ) > 0 ) )

                        if (bomb):

                            # Lower bomb count, if they're not free...
                            #if ( wave_tracker.get_wave_param("bombs-free") != 1 ):
                            if ( not ( universe.get_active_map().get_param("type") in ("puzzle", "challenge") ) ):

                                # They're not unlimited!
                                universe.increment_session_variable("core.bombs.count", -1)


                            # Always track that we did just use a bomb
                            wave_tracker.increment_wave_counter("bombs", 1)

                            # Update map param that tracks bombs used
                            universe.get_active_map().set_param(
                                "stats.bombs-used",
                                1 + universe.get_active_map().get_param("stats.bombs-used")
                            )


                            # Place bomb sound effect
                            control_center.get_sound_controller().queue_sound(SFX_PLACE_BOMB)


            if (INPUT_ACTIVATE_SKILL_1 in user_input):

                result = self.activate_skill( universe.get_session_variable("core.player1.skill1").get_value(), control_center, universe )

                # Activated successfully?
                if (result):

                    # Update map param that tracks how many times we've used a skill
                    m.set_param(
                        "stats.skills-used",
                        1 + m.get_param("stats.skills-used")
                    )

            elif (INPUT_ACTIVATE_SKILL_2 in user_input):

                result = self.activate_skill( universe.get_session_variable("core.player1.skill2").get_value(), control_center, universe )

                # Activated successfully?
                if (result):

                    # Update map param that tracks how many times we've used a skill
                    m.set_param(
                        "stats.skills-used",
                        1 + m.get_param("stats.skills-used")
                    )


        if (not self.moved_this_frame):

            if ( any( e in previous_input_copy for e in (INPUT_MOVE_LEFT, INPUT_MOVE_RIGHT, INPUT_MOVE_UP, INPUT_MOVE_DOWN) ) ):

                network_controller.send_entity_stop_motion(
                    entity = self,
                    control_center = control_center,
                    universe = universe
                )



        if ("reset" in user_input):
            self.is_climbing = False


    # Equip a given skill to a given slot
    def equip_skill_in_slot(self, skill_name, slot, control_center, universe):

        # Update session variable
        universe.get_session_variable("core.player1.skill%s" % slot).set_value(skill_name)

        # Set a flag indicating that the player changed a skill slot.
        # This will inform the HUD that it needs up update its text cache...
        # (This no doubt is a bad hack!)
        universe.set_session_variable("core.player1.skill%d:changed" % slot, "1")
        # Clear HUD cache
        #control_center.get_window_controller().clear_cache()


    #def activate_skill(self, name, universe, p_map, session, scripted = False):
    def activate_skill(self, skill_name, control_center, universe, scripted = False):

        # If this skill has not finished recharging, we cannot use it...
        if (not scripted):

            if ( int( universe.get_session_variable("core.skills.%s:recharge-remaining" % skill_name).get_value() ) > 0 ):

                # Try again when it recharges...
                return False


        # Get the stats associated with this skill / level
        stats = universe.get_skill_stats().get_skill_stats_by_level(skill_name, int( universe.get_session_variable("core.skills.%s" % skill_name).get_value() ))

        # If we didn't find stats, we'll have to abort...
        if (stats == None):
            return False


        # Sprint?
        if (skill_name == "sprint"):

            # Fetch active map
            m = universe.get_active_map()


            # Set the duration
            universe.set_session_variable( "core.skills.sprint:timer", "%d" % stats.get_duration() )

            # Set Sprint bonus
            self.sprint_bonus = ( stats.get_modifier_by_name("sprint-power-factor") * self.get_speed(universe) ) - self.get_speed(universe)

            # Fun test...
            if ( stats.get_modifier_by_name("kill-all-enemies") == 1.0 ):

                for e in m.get_entities_by_type(GENUS_ENEMY):

                    e.queue_death_by_cause(DEATH_BY_VAPORIZATION)


            # Track timer, recharge, etc.
            if (not scripted):

                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True


        # Invisibility?
        elif (skill_name == "invisibility"):

            # Set the duration to "duration * power-drain"
            universe.set_session_variable("core.skills.invisibility:timer", "%d" % int( stats.get_duration() * stats.get_modifier_by_name("timer-drain") ))

            # Track power drain while moving / motionless
            universe.set_session_variable("core.skills.invisibility:timer-drain", "%d" % int( stats.get_modifier_by_name("timer-drain") ))
            universe.set_session_variable("core.skills.invisibility:timer-drain-while-motionless", "%d" % int( stats.get_modifier_by_name("timer-drain-while-motionless") ))


            # Duration indicator?
            #p_map.requested_header_hook = self.get_invisibility_bar_data


            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True


        # Matrix effect
        elif (skill_name == "matrix"):

            # Fetch active map
            m = universe.get_active_map()


            # Get the duration
            m.master_plane.matrix_remaining = stats.get_duration()

            # Calculate how many frames to skip enemy/etc. processing for...
            m.master_plane.set_matrix_frame_delay( int( stats.get_modifier_by_name("frame-delay") ) )


            # Numbercle effect; calculate center of effect
            (cx, cy) = (
                self.get_x() + int(self.width / 2),
                self.get_y() + int(self.height / 2)
            )

            # Apply effect
            for i in range(0, 25):

                m.numbercles.append(
                    Numbercle(cx + random.randint(-8, 8), cy + random.randint(-8, 8), random.randint(0, 9))
                )


            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True


        # Personal shield?
        elif (skill_name == "personal-shield"):

            # Fetch active map
            m = universe.get_active_map()

            # Set shield amount and original potential
            #self.shield_potential = 100
            #self.shield_amount = 100

            # Set the duration to "duration * power-drain"
            universe.set_session_variable("core.skills.personal-shield:timer", "%d" % int( stats.get_duration() * stats.get_modifier_by_name("timer-drain") ))


            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)

            # Old?  Use still?
            if (not scripted):
                m.requested_header_hook = self.get_shield_bar_data


            # Activate shield for this player entity
            self.has_shield = True


            # Skill used successfully
            return True


        # Magic wall?
        elif (skill_name == "wall"):

            if (self.direction == DIR_LEFT):

                self.place_magic_wall_left(
                    universe,
                    lifespan = stats.get_duration(),
                    has_spikes = ( int( stats.get_modifier_by_name("has-spikes") ) == 1 )
                )

            else:

                self.place_magic_wall_right(
                    universe,
                    lifespan = stats.get_duration(),
                    has_spikes = ( int( stats.get_modifier_by_name("has-spikes") ) == 1 )
                )


            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True


        # Pickpocket?
        elif (skill_name == "pickpocket"):

            # Fetch active map
            m = universe.get_active_map()


            # Determine range
            max_range = TILE_WIDTH * int( stats.get_modifier_by_name("effective-radius") )


            # Square it for pythagorean calculation...
            max_range_squared = max_range * max_range

            # Player coordinates (center)
            (x1, y1) = (
                self.get_x() + int(self.width / 2),
                self.get_y() + int(self.height / 2)
            )


            # Find nearby enemies...
            for genus in (GENUS_ENEMY,):

                for entity in m.master_plane.entities[genus]:

                    # Enemy coordinates (center)
                    (x2, y2) = (
                        entity.get_x() + int(entity.width / 2),
                        entity.get_y() + int(entity.height / 2)
                    )

                    # Calculate distance (but don't bother taking square root...)
                    distance_squared = ((x2 - x1) * (x2 - x1)) + ((y2 - y1) * (y2 - y1))

                    # Within range?
                    if (distance_squared <= max_range_squared):

                        # If the enemy has gold, mark it as collected (and thus the enemy will not be carrying gold any longer...)
                        if (entity.ai_state.ai_is_carrying_gold):

                            # Check the handle to the gold they're carrying...
                            gold = m.get_entity_by_name( entity.ai_state.ai_is_carrying_gold_by_name )

                            # Collect that gold...
                            self.collect_gold_entity(gold, control_center, universe)


                            # Flag the enemy as no longer carrying gold
                            entity.ai_state.ai_is_carrying_gold = False
                            entity.ai_state.ai_is_carrying_gold_by_name = ""
                            

            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True


        # Jackhammer?
        elif (skill_name == "jackhammer"):

            dig_result = self.dig_to_direction(
                self.direction,
                control_center,
                universe,                    
                depth = stats.get_modifier_by_name("dig-power"),
                duration_multiplier = stats.get_modifier_by_name("dig-duration-multiplier")
            )

            if (dig_result == DIG_RESULT_SUCCESS):

                # Track timer, recharge, etc.
                if (not scripted):

                    self.track_skill_metrics_from_stats(skill_name, stats, universe)


                # Skill used successfully
                return True

            else:

                # Skill not used, nowhere to dig
                return False


        # Earth-mover?
        elif (skill_name == "earth-mover"):

            dig_result = self.dig_to_direction(
                self.direction,
                control_center,
                universe,
                distance = stats.get_modifier_by_name("dig-power"),
                duration_multiplier = stats.get_modifier_by_name("dig-duration-multiplier")
            )

            if (dig_result == DIG_RESULT_SUCCESS):

                # Track timer, recharge, etc.
                if (not scripted):
                    self.track_skill_metrics_from_stats(skill_name, stats, universe)


                # Skill used successfully
                return True

            else:

                # Skill not used, nowhere to dig
                return False


        # Mega bomb
        elif (skill_name == "mega-bomb"):

            # Fetch active map
            m = universe.get_active_map()

            # Also grab the wave tracker
            wave_tracker = m.get_wave_tracker()


            # Make sure we have enough bomb fuel
            bomb_requirement = 1 + int( stats.get_modifier_by_name("additional-bombs-required-for-fuel") )

            # If bombs on this map wave are not free, then we need to have enough bombs to fuel this mega bomb...
            if ( (wave_tracker.count_free_bombs_remaining() >= bomb_requirement) or (int( universe.get_session_variable("core.bombs.count").get_value() ) >= bomb_requirement) ):

                # Which direction to bomb?
                if ( self.direction in (DIR_LEFT, DIR_RIGHT) ):

                    bomb = self.bomb_to_direction(self.direction, control_center, universe, radius = 1 + int( stats.get_modifier_by_name("radius-bonus") ), remote = False)

                    if (bomb):

                        # Take away the bombs required, unless we're in a cutscene (e.g. gif)
                        if (not scripted):

                            # If bombs are free on this map wave, we don't decrement...
                            if ( wave_tracker.get_wave_param("bombs-free") != 1 ):

                                # We just used n bombs to fuel the mega bomb
                                universe.increment_session_variable("core.bombs.count", -1 * bomb_requirement)


                            # Always note that we just used N bombs for this mega bomb
                            wave_tracker.increment_wave_counter("bombs", bomb_requirement)


                            # Track timer, recharge, etc.
                            self.track_skill_metrics_from_stats(skill_name, stats, universe)


                        # Skill used successfully
                        return True

                    else:

                        # Skill not used, can't put a bomb there
                        return False

            else:

                # Not enough bombs to use the skill
                return False


        # Remotely detonated bomb
        elif (skill_name == "remote-bomb"):

            # Fetch the active map
            m = universe.get_active_map()

            # Get the wave tracker, too
            wave_tracker = m.get_wave_tracker()


            # If we have already placed a bomb, the second skill use will detonate that bomb...
            if ( len(self.remote_bombs) > 0 ):

                # Blow them up!
                for bomb in self.remote_bombs:

                    bomb.explode(corpse = True, radius = bomb.radius, control_center = control_center, universe = universe)

                # No more remote bomb...
                self.remote_bombs = []


                # NOW is the time to track recharge, etc.!
                if (not scripted):

                    self.track_skill_metrics_from_stats(skill_name, stats, universe)


                # Skill used successfully
                return True


            # Otherwise, lay down a remote bomb.  We won't track metrics (i.e. recharge time) until final detonation.
            # We can also use a remote bomb at any time if bombs are free.  Make sure we have a bomb available to place, too!
            elif ( (wave_tracker.count_free_bombs_remaining() >= 1) or (int( universe.get_session_variable("core.bombs.count").get_value() ) >= 1) ):

                if ( self.direction in (DIR_LEFT, DIR_RIGHT) ):

                    bomb = self.bomb_to_direction(self.direction, control_center, universe, radius = 1, remote = True)

                    if (bomb):

                        # Define how many more remote bombs we can possibly place...
                        universe.set_session_variable("core.skills.remote-bomb:bombs-remaining", "%d" % int( stats.get_modifier_by_name("additional-concurrent-bombs") ))

                        # Take away the bombs required, unless we're in a cutscene (e.g. gif)
                        if (not scripted):

                            # Don't decrement bomb inventory if bombs are "free"
                            if ( wave_tracker.get_wave_param("bombs-free") != 1 ):

                                # One less bomb in our inventory
                                universe.increment_session_variable("core.bombs.count", -1)


                            # Always increment the wave's record of bombs used
                            wave_tracker.increment_wave_counter("bombs", 1)


        # Hologram?
        elif (skill_name == "hologram"):

            # Fetch active map
            m = universe.get_active_map()


            # Create a hologram at the player's current position, traveling in the player's current direction...
            hologram = Hologram(
                "player1.hologram",
                author = self,
                direction = self.direction,
                lifespan = stats.get_duration(),
                exploding = ( int( stats.get_modifier_by_name("explode-on-impact") ) == 1 ),
                collecting = ( int( stats.get_modifier_by_name("collect-gold") ) == 1 )
            )

            # Set the position...
            hologram.x = self.get_x()
            hologram.y = self.get_y()

            # Add it to the NPC list (because it's basically an NPC)
            m.master_plane.entities[GENUS_HOLOGRAM].append(hologram)


            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True


        # Fright effect
        elif (skill_name == "fright"):

            # Fetch active map
            m = universe.get_active_map()


            # Set the fright value for the master plane
            for genus in (GENUS_ENEMY,):

                for entity in m.master_plane.entities[genus]:

                    # Make the enemy scared for the appropriate duration...
                    entity.ai_state.ai_fright_remaining = stats.get_duration()

                    # Let's calculate the chance for this enemy to spontaneously explode...
                    if ( random.random() < stats.get_modifier_by_name("chance-to-spontaneously-explode") ):

                        # Bye-bye, enemy!
                        entity.queue_death_by_cause(DEATH_BY_VAPORIZATION)

                        # Let's do them a favor and reset their fright, at least...
                        entity.ai_state.ai_fright_remaining = 0


            # Define the center for some weird fright particle effect
            (cx, cy) = (
                self.get_x() + int(self.width / 2),
                self.get_y() + int(self.height / 2)
            )

            # I use the last 2 numbercles (? and !) for the fright effect
            for i in range(0, 20):

                m.numbercles.append(
                    Numbercle(cx + random.randint(-8, 8), cy + random.randint(-8, 8), random.randint(10, 11))
                )


            # Track timer, recharge, etc.
            if (not scripted):
                self.track_skill_metrics_from_stats(skill_name, stats, universe)


            # Skill used successfully
            return True

        else:
            log( "unknown skill '%s'" % skill_name )
            log( 5/0 )


        # If we haven't returned success yet, then we'll assume we didn't execute the skill.
        return False



    # Set skill timer / recharge session data.  Used when we activate an active skill.
    def track_skill_metrics_from_stats(self, skill, stats, universe):

        universe.set_session_variable( "core.skills.%s:timer-max" % skill, universe.get_session_variable("core.skills.%s:timer" % skill).get_value() )

        # Player inventory can affect skill recharge time.
        # For whatever reason, I set recharge to count by seconds rather than a percentage.
        # Also, the item attribute always measures in seconds, so I convert it to frames here.
        delta = ( 60 * sum( o.attributes["skill-recharge-adjustment"] for o in universe.get_equipped_items() ) ) # 60 FPS (hard-coded)

        # Set recharge time (and potential, for progress bar calculations).
        # Use max() function to require at least 1 second of recharge time.  (Should always be multiple seconds, but who knows?)
        universe.set_session_variable( "core.skills.%s:recharge-remaining" % skill, "%d" % max(1, stats.get_recharge_time() - delta) )
        universe.set_session_variable( "core.skills.%s:recharge-potential" % skill, "%d" % max(1, stats.get_recharge_time() - delta) )

        universe.set_session_variable( "core.skills.%s:timer-drain" % skill, "%d" % stats.get_modifier_by_name("timer-drain") )
        universe.set_session_variable( "core.skills.%s:timer-drain-while-motionless" % skill, "%d" % stats.get_modifier_by_name("timer-drain-while-motionless") )


    # Collect a given piece of gold
    def collect_gold_entity(self, gold, control_center, universe):

        # Mark the piece of gold as collected by this player
        gold.mark_as_collected_by_actor(control_center, universe, actor = self)#network_controller, universe, p_map, session, actor = self)


        # Get the active map
        m = universe.get_active_map()

        # Also, get the active map's wave tracker
        wave_tracker = m.get_wave_tracker()


        # Mark down another piece of gold collected on this wave
        wave_tracker.increment_wave_counter("gold", 1)

        # Check to see if we have a script to run when we collect a piece of gold
        if ( m.does_script_exist( wave_tracker.get_wave_param("on-collect-gold") ) ):

            # Run that script now
            m.run_script(
                wave_tracker.get_wave_param("on-collect-gold"),
                control_center,
                universe
            )


    # Increase the player's XP points.  Level up when applicable.
    def increase_xp(self, amount, control_center, universe):

        log2( "Increase xp by %s" % amount )

        # Get level xp requirements from the universe
        level_xp_requirements = universe.get_level_xp_requirements()


        # Grab current character level
        level = int( universe.get_session_variable("core.player1.level").get_value() )

        # Get current XP amount
        old_xp = int( universe.get_session_variable("core.player1.xp").get_value() )


        # Calculate new xp amount
        new_xp = old_xp + amount
        log2( "XP report:  old, new = ", (old_xp, new_xp) )

        # Track new XP immediately
        universe.set_session_variable("core.player1.xp", "%d" % new_xp)


        # Check to see if we've cleared the minimum XP for any higher level (level up)
        for level_xp_requirement in level_xp_requirements:

            # we can only level up if we haven't yet reached this character level
            if ( level < level_xp_requirement["level"] ):

                # Have we passed the minimum?
                if ( new_xp >= level_xp_requirement["xp"] ):

                    # Level up!
                    self.level_up(control_center, universe)


                    # Update local variable
                    level += 1

                    # Set the "old_xp" variable to this new level's minimum (helps with percentage calculations)
                    old_xp = level_xp_requirement["xp"]


                    # Execute the "leveled-up" achievement hook
                    universe.execute_achievement_hook( "leveled-up", control_center )


        #print level_xp_requirements


        # If the player has the chance to level up (more levels remain), we'll update the progress bar's
        # parameters and such.
        if ( len(level_xp_requirements) > (level + 1) ):

            log2( "Current level = %s" % level )

            # Calculate the difference between the next level's xp requirement and the current level's xp requirement (denominator)
            b = ( level_xp_requirements[ (level + 1) - 1 ]["xp"] - level_xp_requirements[ level - 1 ]["xp"] )


            # Calculate how much of that span the player had covered before earning the current XP bonus
            xp_percent_old = ( float( old_xp - level_xp_requirements[ level - 1 ]["xp"] ) / float(b) )

            # Calculate how close they have come to the next available "level up" after the current XP bonus
            xp_percent_new = ( float( new_xp - level_xp_requirements[ level - 1 ]["xp"] ) / float(b) )


            log2( "xp_percent_old = %s" % xp_percent_old )
            log2( "xp_percent_new = %s" % xp_percent_new )
            log2( "    b = %s" % b )


            # Update session's xp bar data
            universe.set_session_variable( "core.xp-bar.percent-old", "%f" % xp_percent_old )
            universe.set_session_variable( "core.xp-bar.percent-new", "%f" % xp_percent_new )

            # Update timer-related data; show the bar for a short duration.
            universe.set_session_variable( "core.xp-bar.timer", "%d" % XP_BAR_ANIMATION_DURATION )
            universe.set_session_variable( "core.xp-bar.timer-max", "%d" % XP_BAR_ANIMATION_DURATION )


            # Update XP earned / needed subtitle data
            universe.set_session_variable( "core.xp-bar.total-earned", "%d / %d XP" % ( new_xp, level_xp_requirements[ (level - 1) + 1 ]["xp"] ) )


    # Character levels up.
    def level_up(self, control_center, universe):

        # Increase player level
        universe.increment_session_variable("core.player1.level", 1)

        # Add a skill point
        universe.increment_session_variable("core.player1.skill-points", 1)


        # Submit a "leveled up!" newsfeeder message
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_CHARACTER_LEVEL_UP,
            "character-level": xml_encode( universe.get_session_variable("core.player1.level").get_value() ),
            "skill-points": xml_encode( universe.get_session_variable("core.player1.skill-points").get_value() )
        })


    def get_shield_bar_data(self, universe):

        label = ""

        (shield_amount, shield_potential) = (
            int( universe.get_session_variable("core.skills.personal-shield:timer").get_value() ),
            int( universe.get_session_variable("core.skills.personal-shield:timer-max").get_value() )
        )


        if (shield_amount == shield_potential):
            label = "Personal Shield Activated"


        return (
            (shield_amount / float(shield_potential)),
            SHIELD_BAR_COLOR,
            label,
            (shield_amount <= 0)
        )


    def get_invisibility_bar_data(self, universe):

        label = ""

        (invisibility_amount, invisibility_potential) = (
            int( universe.get_session_variable("core.skills.invisibility:timer").get_value() ),
            int( universe.get_session_variable("core.skills.invisibility:timer-max").get_value() )
        )


        if (invisibility_amount == invisibility_potential):
            label = "Invisibility Activated"


        return (
            (invisibility_amount / float(invisibility_potential)),
            INVISIBILITY_BAR_COLOR,
            label,
            (invisibility_amount <= 0)
        )


    def get_disguise_bar_data(self, universe):

        log( self.name, self )

        label = ""

        (disguise_amount, disguise_potential) = (
            int( universe.get_session_variable("core.skills.disguise:timer").get_value() ),
            int( universe.get_session_variable("core.skills.disguise:timer-max").get_value() )
        )


        if (disguise_amount == disguise_potential):
            label = "Disguise Activated"


        return (
            (disguise_amount / float(disguise_potential)),
            DISGUISE_BAR_COLOR,
            label,
            (disguise_amount <= 0)
        )


    def handle_entity_touch(self, entity, control_center, universe):

        if ( entity.genus == GENUS_ENEMY ):

            # Player inventory might give the player a chance of killing the enemy instead
            chance = sum( o.attributes["reverse-kill-probability"] for o in universe.get_equipped_items() )

            # Any chance?
            if (chance > 0):

                # Roll the dice
                if (random.random() <= chance):

                    # Kill the enemy instead...
                    entity.queue_death_by_cause(DEATH_BY_VAPORIZATION)

                # No luck
                else:

                    # Player loses, game over man
                    self.queue_death_by_cause(DEATH_BY_ENEMY)

            # No chance; enemy wins
            else:

                self.queue_death_by_cause(DEATH_BY_ENEMY)
        #print "%s touched you, %s!" % (entity.name, self.name)

        #f = open( os.path.join("debug", "debug.ai.txt"), "a" )
        #f.write("%s touched %s\n" % (entity.name, self.name))
        #f.close()
        return


    #def die(self, cause, network_controller, universe, p_map, session, with_effects = True, with_logic = True, server_approved = False):
    def die(self, cause, control_center, universe, with_effects = True, with_logic = True, server_approved = False):#, control_center, universe, with_effects = True, with_logic = True, server_approved = False):

        # During netplay, a client can only run death logic for the local player
        #if ( ( network_controller.get_status() == NET_STATUS_OFFLINE ) or ( self == universe.get_local_player() ) ):
        #if ( (server_approved) or ( self == universe.get_local_player() ) ):
        if ( self == universe.get_local_player() ):

            # Check for shield
            if ( self.is_protected_by_shield(cause, universe) ):

                # Shield protects
                return

            # The player's inventory might have an item granting bomb immunity
            elif ( (cause == DEATH_BY_BOMB) and ( sum( o.attributes["bomb-player-immunity"] for o in universe.get_equipped_items() ) > 0 ) ):

                # Immune
                return

            # No immunity found
            else:

                self.set_status(STATUS_INACTIVE)

                # Include effects?
                if (with_effects):

                    # Particle explosion
                    for j in range(0, 3):
                        for i in range(0, 3):

                            self.particles.append( Particle(self.get_x(), self.get_y(), 0, i, j) )

                # Handle logic?
                #if ( self == universe.get_local_player() ):
                #if ( network_controller.get_status() != NET_STATUS_CLIENT ):


                # Handle death logic
                self.handle_death(cause, control_center, universe)#network_controller, universe, p_map, session)


                # If we're playing online, let's add a message to the chatlog for this player death event
                if ( control_center.get_network_controller().get_status() in (NET_STATUS_SERVER, NET_STATUS_CLIENT) ):

                    # Quickly validate that we have the expect name for this player entity.
                    # Yes, this is hacky.
                    if ( self.get_name() in ("player1", "player2", "player3", "player4") ):

                        # Parse out player id
                        player_id = self.get_name().replace("player", "")

                        # Get player nick
                        nick = universe.get_session_variable("net.player%s.nick" % player_id).get_value()

                        # Show "so-and-so died" chat message using known nick
                        control_center.get_network_controller().get_net_console().add(
                            control_center.get_localization_controller().get_label( "n-has-died:message", { "@n": nick } ), text_type = "player-died, player-%s-died" % player_id
                        )
                        #   "[color=special]%s[/color] has died!" % nick )

        else:

            # (?) Notice of another player's death is akin to a "stop motion" event, since they're kind of dead.
            # For now, we'll just stop their motion at the last position we marked them at.  The location is fairly irrelevant, anyway, since they're dead.
            self.handle_message("stop-motion", None, "%s;%s" % ( self.get_x(), self.get_y() ), control_center, universe = universe)#, p_map = m, session = self.session)

            if (server_approved):

                self.set_status(STATUS_INACTIVE)

                # Include effects?
                if (with_effects):

                    # Particle explosion
                    for j in range(0, 3):
                        for i in range(0, 3):

                            self.particles.append( Particle(self.get_x(), self.get_y(), 0, i, j) )

                # If we're playing online, let's add a message to the chatlog for this player death event
                if ( control_center.get_network_controller().get_status() in (NET_STATUS_SERVER, NET_STATUS_CLIENT) ):

                    # Quickly validate that we have the expect name for this player entity.
                    # Yes, this is hacky.
                    if ( self.get_name() in ("player1", "player2", "player3", "player4") ):

                        # Parse out player id
                        player_id = self.get_name().replace("player", "")

                        # Get player nick
                        nick = universe.get_session_variable("net.player%s.nick" % player_id).get_value()

                        # Show "so-and-so died" chat message using known nick
                        control_center.get_network_controller().get_net_console().add(
                            control_center.get_localization_controller().get_label( "n-has-died:message", { "@n": nick } ), text_type = "player-died, player-%s-died" % player_id
                        )# "[color=special]%s[/color] has died!" % nick )

            else:

                #self.set_sync_status(SYNC_STATUS_PENDING)
                #log( "Set '%s' to pending..." % self.name )
                pass


    def handle_death(self, cause, control_center, universe):

        log( "%s death by %d" % (self.name, cause) )

        # Don't use this logic during dummy sessions (e.g. Gifs)
        if ( int( universe.get_session_variable("core.is-dummy-session").get_value() ) != 1 ):

            # Track the cause of player death
            universe.set_session_variable("core.player1.cause-of-death", "%d" % cause)


            # Before we get to the fun stuff, let's see if the map defined a special
            # ondeath script for this entity (e.g. npc1.ondeath)
            script_name = "%s.ondeath" % self.name

            # Fetch network controller;
            network_controller = control_center.get_network_controller()

            # and active map
            m = universe.get_active_map()


            # Special ondeath script for this entity?
            if ( m.does_script_exist(script_name) ):

                m.run_script(script_name, control_center, universe)#, session, universe.quests)


            # Online as server?
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                #universe.net_kill_entity(self, network_controller)
                network_controller.send_entity_die(self, control_center, universe)

            # Online as client?
            elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

                #universe.net_client_announce_death(self, network_controller)
                network_controller.send_entity_die(self, control_center, universe)


    # During netplay, a player can respawn at a given entity (typically a "player respawn point")
    def respawn_at_entity(self, entity, control_center, universe):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # During netplay, the server will reactivate the player, place them at the respawn entity,
        # then sync the player up as active for all clients...
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            # Active
            self.set_status(STATUS_ACTIVE)

            # Sync status back to ready
            #self.set_sync_status(SYNC_STATUS_READY)


            # Position
            self.set_xy(
                entity.get_x(),
                entity.get_y()
            )


            # Announce respawn to each client
            network_controller.send_respawn_entity_at_entity(self, entity, control_center, universe)

            # Remove "so and so died" message.
            # (First, parse out player id.)
            player_id = self.get_name().replace("player", "")
            network_controller.get_net_console().remove_lines_by_class("player-%s-died" % player_id)


        # During netplay, a client will simply reactivate the given player entity
        elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

            # Active
            self.set_status(STATUS_ACTIVE)

            # Sync status back to ready
            #self.set_sync_status(SYNC_STATUS_READY)


            # Position
            self.set_xy(
                entity.get_x(),
                entity.get_y()
            )


            # Remove "so and so died" message.
            # (First, parse out player id.)
            player_id = self.get_name().replace("player", "")
            network_controller.get_net_console().remove_lines_by_class("player-%s-died" % player_id)


    def queue_dig(self, tx, ty, direction, depth = 1, distance = 1, duration_multiplier = 1):

        self.queued_digs.append({
            "timer": DIG_QUEUE_TIME,
            "direction": direction,
            "tile-coords": (tx, ty),
            "depth": depth,
            "distance": distance,
            "duration-multiplier": duration_multiplier
        })


    # Check queued digs on some map m
    def check_queued_digs_on_map(self, m):

        i = 0

        while (i < len(self.queued_digs)):

            # Decrease the timer
            self.queued_digs[i]["timer"] -= 1

            # Ready to (try to) dig?
            if (self.queued_digs[i]["timer"] <= 0):

                # Fetch the tile coordinates
                (tx, ty) = self.queued_digs[i]["tile-coords"]

                # Try to dig the tile
                result = m.dig_tile_at_tile_coords(tx, ty, duration_multiplier = self.queued_digs[i]["duration-multiplier"])

                # If successful, we can continue to dig more tiles as necessary...
                if (result == DIG_RESULT_SUCCESS):

                    # Queue another dig if we have more depth / distance to cover...
                    if (self.queued_digs[i]["depth"] > 1):

                        # Depth always goes downward...
                        self.queue_dig(tx, ty + 1, DIR_DOWN, depth = self.queued_digs[i]["depth"] - 1, distance = 1, duration_multiplier = self.queued_digs[i]["duration-multiplier"])


                    # Try distance for earth-mover digs
                    if (self.queued_digs[i]["distance"] > 1):

                        # Depends on direction...
                        if (self.queued_digs[i]["direction"] == DIR_LEFT):

                            self.queue_dig(tx - 1, ty, DIR_LEFT, depth = 1, distance = self.queued_digs[i]["distance"] - 1, duration_multiplier = self.queued_digs[i]["duration-multiplier"])

                        elif (self.queued_digs[i]["direction"] == DIR_RIGHT):

                            self.queue_dig(tx + 1, ty, DIR_RIGHT, depth = 1, distance = self.queued_digs[i]["distance"] - 1, duration_multiplier = self.queued_digs[i]["duration-multiplier"])


                # Now that we've handled this queued item, release it
                self.queued_digs.pop(i)

            else:

                i += 1


    def dig_to_direction(self, direction, control_center, universe, depth = 1, distance = 1, duration_multiplier = 1):

        # Look at our feet and see how close they are to the ground.  If we're almost
        # low enough to dig a row, or we're almost high enough to "cheat up" and little
        # bit, then we'll fudge it.
        dy = ( (self.get_y() + self.height) % TILE_HEIGHT )

        # Calculate a fudge factor that determines whether or not we're close enough
        fudge_factor_y = int(0.4 * TILE_HEIGHT)


        # Fetch active map
        m = universe.get_active_map()

        # Also fetch the active map's wave tracker
        wave_tracker = m.get_wave_tracker()


        # If we're in "no man's land" totally between rows), then we won't do anything...
        if ( (dy > fudge_factor_y) and (dy < (TILE_HEIGHT - fudge_factor_y)) ):

            #log2( "dy = ", dy, "not valid for fudge", fudge_factor_y, " .y = %s, height = %s" % (self.get_y(), self.height) )
            return DIG_RESULT_EMPTY

        # Perhaps we do not have any digs left on the map?
        elif ( (wave_tracker.get_wave_allowance("digs") >= 0) and (wave_tracker.get_wave_counter("digs") >= wave_tracker.get_wave_allowance("digs")) ):

            # Can't dig anymore!
            return DIG_RESULT_EMPTY

        # Otherwise, let's try to dig on the nearest row (either up or down)
        else:

            # Declare variables
            (tx, ty) = (-1, -1)

            # Calculate where we would position the player on the y-axis if the dig were to succeed.
            # Assume at first that we're almost "up" to the next row (or at perfect y alignment already!)
            fudged_y = self.get_y() - dy

            # Now, let's check to see if instead we should be cheating "down" a bit...
            if (dy > fudge_factor_y): # If it's greater, then it must be in the 67% - 100% range

                # Adjust down instead of up
                fudged_y = self.get_y() + (TILE_HEIGHT - dy)


            # Which direction?
            if (direction == DIR_LEFT):

                # Aim a little to the left
                guesstimate = self.get_x() - int(self.width / 2)

                # Set target
                (tx, ty) = ( int(guesstimate / TILE_WIDTH), int(fudged_y / TILE_HEIGHT) + 1 )

            elif (direction == DIR_RIGHT):

                # Aim a little to the right
                guesstimate = (self.get_x() + self.width) + int(self.width / 2)

                # Set target
                (tx, ty) = ( int(guesstimate / TILE_WIDTH), int(fudged_y / TILE_HEIGHT) + 1 )


            # If we commit to this dig, where would we align the player to?  (perfect alignment)
            perfect_x = self.get_x()
            perfect_y = fudged_y

            # Perfect alignment, depending on direction...
            if (direction == DIR_LEFT):

                perfect_x = (tx * TILE_WIDTH) + TILE_WIDTH

            elif (direction == DIR_RIGHT):

                perfect_x = (tx * TILE_WIDTH) - self.width


            # Ensure that aligning to that position would not overlap us with any other entity...
            if ( m.count_enemies_in_rect( (perfect_x, perfect_y, self.width, self.height), exceptions = (self,) ) == 0 ):

                # Where will the player be standing (in tile coordinates) after the dig?  It will have to be solid ground / a ladder / a monkey bar, etc...
                perfect_tx = int( perfect_x / TILE_WIDTH )

                # Ensure that we can validly dig that tile...
                #if ( (m.master_plane.check_collision(perfect_tx, ty) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_BRIDGE, COLLISION_LADDER)) or
                #     (m.master_plane.check_collision(perfect_tx, ty - 1) in (COLLISION_LADDER, COLLISION_MONKEYBAR)) ):
                if (
                    self.can_walk_over_tile(perfect_tx, ty, m)
                ):


                    # Try to dig
                    result = m.dig_tile_at_tile_coords(
                        tx,
                        ty,
                        duration_multiplier = duration_multiplier
                    )


                    # You can't dig empty / already-dug tiles; do nothing...
                    if (result == DIG_RESULT_EMPTY):

                        pass

                    # Successful dig?  Dig animation, generate particles...
                    elif (result == DIG_RESULT_SUCCESS):

                        # Perfect alignment, depending on direction...
                        if (direction == DIR_LEFT):

                            self.set_x( (tx * TILE_WIDTH) + TILE_WIDTH )
                            self.set_y( (ty * TILE_HEIGHT) - self.height )

                        elif (direction == DIR_RIGHT):

                            self.set_x( (tx * TILE_WIDTH) - self.width )
                            self.set_y( (ty * TILE_HEIGHT) - self.height )


                        # Briefly delay player movement due to digging...
                        self.dig_delay = DIG_DELAY

                        # Face dig direction
                        self.set_direction(direction)


                        # If the dig landed us on top of an enemy, we're done...
                        #if ( len( m.query_interentity_collision_for_entity_against_entity_types( (GENUS_ENEMY,), self ).get_results() ) > 0 ):

                        #    # Goodbye cruel world ;)
                        #    self.queue_death_by_cause(DEATH_BY_ENEMY)


                        # Are we using jackhammer or earth-mover, maybe?
                        if (depth > 1):

                            self.queue_dig(tx, ty + 1, DIR_DOWN, depth = depth - 1, duration_multiplier = duration_multiplier)

                        elif (distance > 1):

                            # Earth mover dig, dig to the direction...
                            if (direction == DIR_LEFT):

                                self.queue_dig(tx - 1, ty, direction, distance = distance - 1, duration_multiplier = duration_multiplier)

                            elif (direction == DIR_RIGHT):

                                # Earth mover dig, dig to the right
                                self.queue_dig(tx + 1, ty, direction, distance = distance - 1)


                        # Dig sound effect
                        control_center.get_sound_controller().queue_sound(SFX_PLAYER_DIG)


                        # Increment universe's total digs counter
                        universe.get_session_variable("stats.digs").increment_value(1)

                        # Track that we just used another dig
                        wave_tracker.increment_wave_counter("digs", 1)


                        # Execute the "dig" achievement hook
                        universe.execute_achievement_hook("dig", control_center)


                        # Check to see if we have a script to run when any enemy collects a piece of gold
                        if ( m.does_script_exist( wave_tracker.get_wave_param("on-dig") ) ):

                            # Run that script now
                            m.run_script(
                                wave_tracker.get_wave_param("on-dig"),
                                control_center,
                                universe
                            )


                        # If we set the wave to consider all digs permanent, then let's purge the tile we successfully dug...
                        if ( int( wave_tracker.get_wave_param("digs-purge") ) == 1 ):

                            # Dig the same location, but specify purge.
                            # We don't care about the result, it should work!  Right?!
                            m.dig_tile_at_tile_coords(
                                tx,
                                ty,
                                purge = True,
                                scripted_dig = True, # Kind of...
                                force_dig = True # We dug it away to a 0 tile, so we have to specify force or it'll think we're trying to dig empty air
                            )


                        # Fetch network controller
                        network_controller = control_center.get_network_controller()


                        # Online as server?
                        if ( network_controller.get_status() == NET_STATUS_SERVER ):

                            # Send notice of this dig to all clients
                            network_controller.send_entity_dig(
                                entity = self,
                                direction = direction,
                                tx = tx,
                                ty = ty,
                                control_center = control_center,
                                universe = universe
                            )


                        # Online as client?
                        elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

                            # Key we'll lock with, pending confirmation
                            key = "test.dig1"

                            # Lock the universe pending dig request confirmation.  We'll do the dig anyway for now,
                            # optimistically assuming it'll work (and it usually will).
                            universe.lock_with_key(
                                key = key,
                                timeout = 120,
                                strength = LOCK_HARD
                            )

                            # Send dig validation request to server
                            network_controller.send_entity_dig_validation_request_with_key(
                                key = key,
                                entity = self,
                                tx = tx,
                                ty = ty,
                                direction = direction,
                                control_center = control_center,
                                universe = universe
                            )


                    # Hard ground or something?  Dig animation nonetheless... maybe sparks fly...
                    elif (result == DIG_RESULT_UNDIGGABLE):
                        pass


                    return result

                # Can't dig while standing in mid-air...
                else:

                    return DIG_RESULT_EMPTY

            # If that dig attempt would result in an entity intersection, we can't do it...
            else:

                return DIG_RESULT_UNDIGGABLE


    def place_magic_wall_left(self, universe, lifespan, has_spikes):

        # Can't place a magic wall unless at a solid level...
        if (self.get_y() % TILE_HEIGHT != 0):
            return False


        else:

            # Aim a little to the right
            guesstimate = self.get_x() - int(self.width / 2)

            (tx, ty) = ( int(guesstimate / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT) )


            # Fetch active map
            m = universe.get_active_map()

            # Ensure that we can place a magic wall at that position...
            if ( (m.master_plane.check_collision(tx - 1, ty + 1) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_BRIDGE, COLLISION_LADDER)) or
                 (m.master_plane.check_collision(tx - 1, ty) in (COLLISION_LADDER, COLLISION_MONKEYBAR)) ):

                # Try to place a magic wall on the active map
                result = m.place_magic_wall_at_tile_coords(tx, ty, DIR_LEFT, lifespan, has_spikes)


                # You can't place a magic wall there, apparently
                if (not result):
                    pass

                # Successful wall place
                else:

                    # Perfect alignment
                    self.x = (tx * TILE_WIDTH) + TILE_WIDTH

                    # Face right
                    self.set_direction(DIR_LEFT)

                    # Dig sound effect
                    #self.queue_sound(SFX_PLAYER_DIG)


                return result

            # Can't dig while standing in mid-air...
            else:
                return False


    def place_magic_wall_right(self, universe, lifespan, has_spikes):

        # Can't place a magic wall unless at a solid level...
        if (self.get_y() % TILE_HEIGHT != 0):
            return False


        else:

            # Aim a little to the right
            guesstimate = (self.get_x() + self.width) + int(self.width / 2)

            (tx, ty) = ( int(guesstimate / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT) )


            # Fetch active map
            m = universe.get_active_map()

            # Ensure that we can place a magic wall at that position...
            if ( (m.master_plane.check_collision(tx - 1, ty + 1) in (COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_BRIDGE, COLLISION_LADDER)) or
                 (m.master_plane.check_collision(tx - 1, ty) in (COLLISION_LADDER, COLLISION_MONKEYBAR)) ):

                # Try to dig
                result = m.place_magic_wall_at_tile_coords(tx, ty, DIR_RIGHT, lifespan, has_spikes)


                # You can't place a magic wall there, apparently
                if (not result):
                    pass

                # Successful wall place
                else:

                    # Perfect alignment
                    self.x = (tx * TILE_WIDTH) - self.width

                    # Face right
                    self.set_direction(DIR_RIGHT)

                    # Dig sound effect
                    #self.queue_sound(SFX_PLAYER_DIG)


                return result

            # Can't dig while standing in mid-air...
            else:
                return False


    # Bomb to a given direction
    def bomb_to_direction(self, direction, control_center, universe, radius = 1, remote = False):

        # Declare variables
        (tx, ty) = (0, 0)


        # Calculate desired destination depending on direction
        if (direction == DIR_LEFT):

            # Aim a little to the left
            guesstimate = self.get_x() - int(self.width / 2)

            (tx, ty) = ( int(guesstimate / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT) )

        elif (direction == DIR_RIGHT):

            # Aim a little to the right
            guesstimate = (self.get_x() + self.width) + int(self.width / 2)

            (tx, ty) = ( int(guesstimate / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT) )


        # Fetch active map
        m = universe.get_active_map()

        # Also grab the map's wave tracker
        wave_tracker = m.get_wave_tracker()


        # Make sure that the map will allow us to bomb, first of all...
        if ( ( universe.get_active_map().get_param("type") in ("puzzle", "challenge") ) and (wave_tracker.get_wave_allowance("bombs") >= 0) and (wave_tracker.get_wave_counter("bombs") >= wave_tracker.get_wave_allowance("bombs")) ):

            # We can't drop any more bombs.
            return None

        # Ensure that we can validly place a bomb there... no tile in the way...
        elif ( (m.master_plane.check_collision(tx, ty) in (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR)) ):

            # Create a new bomb entity
            bomb = m.create_bomb_with_unique_id(
                x = (tx * TILE_WIDTH),
                y = (ty * TILE_HEIGHT)
            )


            # Update radius
            bomb.set_radius(radius)


            # The player's inventory can alter the bomb's fuse length
            modifier = (
                1.0 +
                sum( o.attributes["bomb-fuse-bonus"] for o in universe.get_equipped_items() )
            )

            # Update fuse length
            bomb.set_fuse_length(
                modifier * bomb.get_fuse_length()
            )


            # Remote bomb?
            if (remote):

                # Tag it and track it!
                self.tag_bomb_as_remote(bomb)

                # One less concurrent remote bomb available, if we had any in the first place...
                if ( int( universe.get_session_variable("core.skills.remote-bomb:bombs-remaining").get_value() ) > 0 ):

                    universe.increment_session_variable("core.skills.remote-bomb:bombs-remaining", -1)


            # Fetch network controller
            network_controller = control_center.get_network_controller()


            # During netplay, clients must confirm the bomb with the server before it can officially
            # begin processing.
            if ( network_controller.get_status() == NET_STATUS_CLIENT ):

                # Lock the bomb, pending validation
                bomb.lock()


                # Define a unique key for this bomb
                key = "validate.%s" % bomb.name

                # Create a faux lock
                universe.lock_with_key(
                    key = key,
                    timeout = 120,
                    strength = LOCK_NONE,
                    f_on_timeout = None
                )

                # Request confirmation that we can place the bomb at the given location
                network_controller.send_bomb_validation_request_with_key(
                    key = key,
                    bomb = bomb,
                    control_center = control_center,
                    universe = universe
                )

            # During netplay, the server does not need to validate the bomb (server controls session),
            # but the server DOES need to send notice of the new bomb to all clients.
            elif ( network_controller.get_status() == NET_STATUS_SERVER ):

                # A simple call
                network_controller.send_create_bomb(bomb, control_center, universe)


            # Just before we return the new bomb, let's increment the universe's bombs used counter
            universe.get_session_variable("stats.bombs-used").increment_value(1)


            # Execute the "placed-bomb" achievement hook
            universe.execute_achievement_hook( "placed-bomb", control_center )


            # Return new bomb object
            return bomb

        else:

            return None


    def tag_bomb_as_remote(self, bomb):

        # Make the bomb a remote bomb
        bomb.make_remote()

        # Append a reference to the bomb to our remote bombs list...
        self.remote_bombs.append(bomb)


    def animate(self):

        self.frame_interval -= 1

        if (self.frame_interval <= 0):

            # Reset delay
            self.frame_interval = self.frame_delay

            # Animate
            self.frame += 1

            if ( self.frame >= self.frame_indices[self.direction].get_sequence_length() ):
                self.frame = 0


    #def process(self, network_controller, universe, p_map, session):
    def process(self, control_center, universe):

        # Fetch active map
        m = universe.get_active_map()


        # Gravity processing
        if (self.status == STATUS_ACTIVE):

            # Check for cached gravity calculation
            gravity = universe.get_cached_item_attribute_result("player-gravity")

            # No cached value?
            if (gravity == None):

                # Calculate modifier
                modifier = (
                    1.0 +
                    sum( o.attributes["player-gravity-bonus"] for o in universe.get_equipped_items() )
                )

                # Calculate value
                gravity = (modifier * RATE_OF_GRAVITY)

                # Cache
                universe.cache_item_attribute_result("player-gravity", gravity)
                    

            self.do_gravity(gravity, universe)#, p_map, session = session)


            # Check for squishing
            if (self.width < 4 or self.height < 4):

                self.queue_death_by_cause(DEATH_BY_PLANAR_SHIFT)


        # Has the player collected any gold?
        entity = self.fetch_first_touched_gold(control_center, universe)#network_controller, universe, p_map, session)

        # Are we touching any gold?  If so, collect it...
        if (entity):

            # Let's make sure the player's allowed to collect gold directly.
            if ( m.get_wave_tracker().get_wave_param("players-collect-gold") == 1 ):

                # Collect the gold!
                self.collect_gold_entity(entity, control_center, universe)


                # Player inventory can offer the player a chance to win more gold...
                for item in universe.get_equipped_items():

                    # Does this item offer that chance?
                    chance = item.attributes["gold-pickup-jackpot-chance"]

                    # Any chance?
                    if (chance > 0):

                        # Roll the dice
                        if (random.random() <= chance):

                            # Add in more gold to the player's wallet, but don't count these as pieces of the gold that the player "found."
                            universe.get_session_variable("core.gold.wallet").increment_value(
                                item.attributes["gold-pickup-jackpot-amount"]
                            )


        # Check for any queued digs (jackhammer / earth-mover)
        self.check_queued_digs_on_map(m)


        # Decrement footstep interval.
        self.footstep_interval -= 1

        # Wrap
        if (self.footstep_interval < 0):

            # Back to max
            self.footstep_interval = FOOTSTEP_INTERVAL_MAX


        # Reduce duration / recharge timers, if applicable, on active skills...
        if ( universe.session_variable_exists("core.player1.skill1") ):# in session):

            skill_keys = (
                universe.get_session_variable("core.player1.skill1").get_value(),
                universe.get_session_variable("core.player1.skill2").get_value()
            )

            for key in skill_keys:

                if (key in ACTIVE_SKILL_LIST):

                    (timer, recharge_remaining) = (
                        int( universe.get_session_variable("core.skills.%s:timer" % key).get_value() ),
                        int( universe.get_session_variable("core.skills.%s:recharge-remaining" % key).get_value() )
                    )

                    # Reduce duration timer?
                    if (timer > 0):

                        # Each skill has a set timer drain.  Usually this is just -= 1, but occasionally
                        # a skill / level will customize its power drain when the player isn't moving...
                        if (self.moved_this_frame):

                            timer -= int( universe.get_session_variable("core.skills.%s:timer-drain" % key).get_value() )

                        # Motionless?  Usually doesn't matter, but sometimes this value differs...
                        else:

                            timer -= int( universe.get_session_variable("core.skills.%s:timer-drain-while-motionless" % key).get_value() )


                        # Update time remaining...
                        universe.set_session_variable("core.skills.%s:timer" % key, "%d" % timer)

                    # Reduce recharge remaining?
                    if (recharge_remaining > 0):

                        recharge_remaining -= 1

                        universe.set_session_variable("core.skills.%s:recharge-remaining" % key, "%d" % recharge_remaining)


        # XP message display duration
        xp_display_interval = int( universe.get_session_variable("core.xp-bar.timer").get_value() )

        # If it's showing, it won't show forever...
        if (xp_display_interval > 0):

            log( "xp timer:  ", xp_display_interval )

            # We only show the animation for so long...
            universe.increment_session_variable("core.xp-bar.timer", -1)


        # Process particles
        for particle in self.particles:
            particle.process(None)


    #def post_process(self, p_map, session = None):
    def post_process(self, control_center, universe):#network_controller, universe, p_map, session):

        # Check for queued death
        if (self.queued_death_by_cause):

            self.die(self.queued_death_by_cause, control_center, universe, with_effects = True)#network_controller, universe, p_map, session, with_effects = True)

            # Reset flag
            self.queued_death_by_cause = None


        # Remove lost particles
        i = 0

        while (i < len(self.particles)):

            if (self.particles[i].state == False):
                self.particles.pop(i)

            else:
                i += 1


        # Able to dig again?
        if (self.dig_delay > 0):
            self.dig_delay -= 1


        # If we're sprinting, see if we've run out of sprint...
        if (self.sprint_bonus > 0):

            # Timer down...
            universe.increment_session_variable("core.skills.sprint:timer", -1)

            # Out of sprint?
            if ( int( universe.get_session_variable("core.skills.sprint:timer").get_value() ) <= 0 ):

                # No more sprint bonus
                self.sprint_bonus = 0


        # Invisible?
        invisibility_remaining = int( universe.get_session_variable("core.skills.invisibility:timer").get_value() )

        # True / False
        self.is_invisible = (invisibility_remaining > 0)


    def xrender_scaled(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        if ( (self.status == STATUS_ACTIVE) and (not self.collected) ):

            # Calculate scaled rect
            rRender = self.get_scaled_rect(scale = scale)

            # Assumed 

            # Get render point
            (rx, ry) = (
                sx + rRender[0],
                sy + rRender[1]
            )

            # Render gold sprite
            window_controller.get_gfx_controller().draw_sprite(rx, ry, self.width, self.height, sprite, scale = scale, gl_color = gl_color, frame = 0)


    def render(self, sx, sy, sprites, scale, is_editor, gl_color, window_controller = None):

        # Before rendering, let's check for any newly queued avatar data (for colors and such)
        if (self.queued_avatar_data != None):

            # Separate the semicolon-separated values
            pieces = self.queued_avatar_data.split(";")


            # Before continuing, let's release the working texture if we need to...
            if (self.working_texture):

                # Later man!
                window_controller.get_gfx_controller().delete_texture(self.working_texture)

                # Posterity
                self.working_texture = None


            # Fetch sprite texture dimensions
            (w, h) = (
                sprites["normal"].get_texture_width(),
                sprites["normal"].get_texture_height()
            )

            # Replicate the default player texture to begin the new working texture
            self.working_texture = window_controller.get_gfx_controller().clone_texture( sprites["normal"].get_texture_id(), w, h )


            # Parse our ssv to see if we should change any color...
            i = 0
            while ( i < len(pieces) ):

                # Convenience
                piece = pieces[i]

                # Validate for format
                if ( piece.find("=") >= 0 ):

                    # key, value
                    (title, new_color) = piece.split("=")

                    # Validate that it's a valid param
                    if (title in DEFAULT_PLAYER_COLORS):

                        # Convert the RGB string into a tuple
                        rgb = parse_rgb_from_string(new_color)

                        # Validate parsing
                        if (rgb):

                            # Replace the old with the new on the working texture...
                            window_controller.get_gfx_controller().replace_color_on_texture(self.working_texture, w, h, DEFAULT_PLAYER_COLORS[title], rgb)


                            # If we just set the "primary" color, then let's remember it as such (for color keying bad guys).
                            # We'll also implicitly add the "primary:bg" color, a downscaled (dimmed) copy of primary.
                            if (title == "primary"):

                                # Track
                                self.primary_color = rgb

                                # Add in a hidden color
                                pieces.append("primary:bg=%s,%s,%s" % ( int(rgb[0] / 2), int(rgb[1] / 2), int(rgb[2] / 2) ))

                # Loop
                i += 1


            # Lastly, reset the queued avatar color data
            self.queued_avatar_data = None


        """
        if (self.network_input != []):
            z = "%s.network_input = %s" % (self.name, self.network_input)
            window_controller.get_default_text_controller().get_text_renderer().render(z, 5, 450, (225, 225, 225))
        """

        if (self.status == STATUS_ACTIVE):

            if ( (is_editor) or (not self.editor_only) ):

                frame = self.frame_indices[self.direction].get_frame_at_sequence_index(self.frame)

                # Special rendering frame for digging...
                if (self.dig_delay > 0):

                    if (self.direction == DIR_LEFT):
                        frame = self.frame_indices[DIR_DIG_LEFT].get_frame_at_sequence_index( (DIG_DELAY - self.dig_delay) )

                    elif (self.direction == DIR_RIGHT):
                        frame = self.frame_indices[DIR_DIG_RIGHT].get_frame_at_sequence_index( (DIG_DELAY - self.dig_delay) )

                # Also for monkey bar swinging...
                elif (self.is_swinging):

                    if (self.direction == DIR_LEFT):
                        frame = self.frame_indices[DIR_SWING_LEFT].get_frame_at_sequence_index(self.frame)

                    elif (self.direction == DIR_RIGHT):
                        frame = self.frame_indices[DIR_SWING_RIGHT].get_frame_at_sequence_index(self.frame)


                # Sometimes we'll render an arrow above the player (during invisibility)
                arrow_width = 8
                arrow_height = 6

                arrow_padding = 4

                # Render point
                (rx, ry) = (
                    sx + int( scale * self.get_x() ),
                    sy + int( scale * self.get_y() )
                )

                if (self.is_invisible > 0):

                    window_controller.get_gfx_controller().draw_sprite(rx, ry, self.width, self.height, sprites["normal"], scale = scale, frame = frame, gl_color = (1, 1, 1, 0.4), hflip = self.frame_indices[self.direction].get_hflip())

                    window_controller.get_geometry_controller().draw_triangle(sx + self.get_x() + int( (self.width - arrow_width) / 2 ), sy + self.get_y() - arrow_height - arrow_padding, arrow_width, arrow_height, (225, 225, 225), (25, 25, 225), DIR_DOWN)

                else:

                    if (self.working_texture):

                        # Provide a texture id overwrite to draw_sprite
                        window_controller.get_gfx_controller().draw_sprite(rx, ry, self.width, self.height, sprites["normal"], scale = scale, gl_color = gl_color, frame = frame, hflip = self.frame_indices[self.direction].get_hflip(), working_texture = self.working_texture)

                    else:

                        # Use the sprite's default texture id
                        window_controller.get_gfx_controller().draw_sprite(rx, ry, self.width, self.height, sprites["normal"], scale = scale, gl_color = gl_color, frame = frame, hflip = self.frame_indices[self.direction].get_hflip())


        # Render particles
        for particle in self.particles:
            particle.render(sx, sy, sprites["normal"], window_controller)


class PlayerRespawn(Entity):

    def __init__(self):

        Entity.__init__(self)

        # Respawn point is inactive by default
        self.set_status(STATUS_INACTIVE)

        self.genus = GENUS_RESPAWN_PLAYER
        self.species = None

        self.editor_only = False

        # No need to track this across sessions, it's a static respawn object
        self.is_ghost = True

        # Track visible text for this respawn point (e.g. "player2" -> "NEW GUY").
        # Default to the name of this object.
        self.visible_text = self.name

        # Create a simple interval controller to animate the
        # "rocking" effect of the respawn graphic (hearT).
        self.rotation_controller = IntervalController(
            interval = 0.0,
            target = 0.0,
            speed_in = 1,
            speed_out = 1
        )

        # Delay briefly before reversing direction
        self.rotation_reversal_delay = 30

        # By default, set the graphic to rotate clockwise to 30 degrees.
        self.rotation_controller.summon(30)


    def activate(self, control_center, universe):

        # Fetch network controller
        network_controller = control_center.get_network_controller()


        # Do not run this if already active
        if ( self.get_status() != STATUS_ACTIVE ):

            # During netplay, the server will activate the respawn point and send a message to each client...
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                self.set_status(STATUS_ACTIVE)

                network_controller.send_respawn_entity_at_entity(self, self, control_center, universe)

            # During netplay, a client will simply enable the respawn point
            elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

                self.set_status(STATUS_ACTIVE)


    def deactivate(self, control_center, universe):

        # Fetch network controller
        network_controller = control_center.get_network_controller()


        # During netplay, the server will deactivate the respawn point and send a message to each client...
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            self.set_status(STATUS_INACTIVE)

            #universe.net_kill_entity(self, network_controller)
            network_controller.send_entity_die(self, control_center, universe)

        # During netplay, a client will simply deactivate the respawn point
        elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

            self.set_status(STATUS_INACTIVE)


    def die(self, cause, control_center, universe, with_effects = True, server_approved = None):#network_controller, universe, p_map, session, with_effects = True, server_approved = None):

        self.set_status(STATUS_INACTIVE)


    def respawn_at_entity(self, respawn_entity, network_controller, universe):

        self.set_status(STATUS_ACTIVE)


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # Calculate player id for this respawn point
        player_name = self.name.split(".")[0]         # e.g. player1.respawn -> player1
        player_id = player_name.replace("player", "") # e.g. player1 -> 1


        # Fetch active map
        m = universe.get_active_map()

        # Is it even active?
        if ( self.get_status() == STATUS_ACTIVE ):

            # Update visible text based on player nick associated with
            # this respawn point's player.
            self.visible_text = "Revive %s" % universe.get_session_variable("net.player%s.nick" % player_id).get_value()

            # Process rocking effect (rock back and forth)
            self.rotation_controller.process()

            # Reached interval?
            if ( self.rotation_controller.get_interval() == self.rotation_controller.get_target() ):

                # Check for reversal delay
                if (self.rotation_reversal_delay > 0):

                    # Tick down
                    self.rotation_reversal_delay -= 1

                # Okay to reverse now
                else:

                    # Update delay
                    self.rotation_reversal_delay = 30

                    # Reverse direction
                    self.rotation_controller.set_target(
                        -1 * self.rotation_controller.get_interval()
                    )


            # During netplay, only the server will handle logic for the thing...
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                # Let's see if any player entity is touching this respawn point
                entities = m.query_interentity_collision_for_entity_against_entity_types( (GENUS_PLAYER,), self ).get_results()

                # If so, we'll deactivate this respawn thing and respawn the player
                if ( len(entities) > 0 ):

                    # Which player does this respawn zone control?
                    player_name = self.name.split(".")[0] # e.g. player1.respawn

                    # Can we find that player?
                    player = m.get_entity_by_name(player_name)

                    # Validate
                    if (player):

                        # Respawn the player at this respawn point's location...
                        player.respawn_at_entity(self, control_center, universe)


                    # The player is going to respawn, so we don't need to keep this respawn point active
                    self.deactivate(control_center, universe)

        # If not, then let's see if the player associated with this respawn zone has died...
        else:

            # During netplay, only the server can control this logic
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                # Which player does this respawn work with?
                player_name = self.name.split(".")[0]

                # Take the last digit as the player id (e.g. player1 -> 1)
                player_id = int( player_name[-1] )


                # Ignore player slots that have not yet joined the game
                if ( universe.get_session_variable("net.player%s.joined" % player_id).get_value() == "1" ):

                    # Find player entity object
                    player = m.get_entity_by_name(player_name)

                    # Validate
                    if (player):

                        # Has the player died?
                        if ( player.get_status() == STATUS_INACTIVE ):

                            # Activate the respawn point for that player
                            self.activate(control_center, universe)


        # Always force this respawn object to inactive if a player has
        # not filled the slot it corresponds to...
        if ( universe.get_session_variable("net.player%s.joined" % player_id).get_value() != "1" ):

            # Force to inactive, don't include server validation / messaging
            self.set_status(STATUS_INACTIVE)


    def render(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        # Always render in editor mode (so we can see it while level editing)
        if ( (is_editor) or (self.status == STATUS_ACTIVE) ):

            if ( (is_editor) or (not self.editor_only) ):

                # Render it at 70% opacity (hard-coded)
                window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, degrees = int( self.rotation_controller.get_interval() ), scale = scale, gl_color = (gl_color[0], gl_color[1], gl_color[2], 0.7 * gl_color[3]))

                window_controller.get_default_text_controller().get_text_renderer().render_with_wrap(self.visible_text, sx + self.get_x() + int(self.width / 2), sy + self.get_y() + 8, (225, 225, 225, 0.5), align = "center")


class Enemy(Entity, ExplodingEntityExt, GoldCollectorEntityExt):

    def __init__(self):

        Entity.__init__(self)
        ExplodingEntityExt.__init__(self)
        GoldCollectorEntityExt.__init__(self)

        self.genus = GENUS_ENEMY
        self.species = SPECIES_NORMAL

        # Define frame indices
        self.frame_indices = {
            DIR_UP: EntityFrameDatum(
                sequence = range(0, 2)
            ),
            DIR_RIGHT: EntityFrameDatum(
                sequence = range(2, 5)
            ),
            DIR_DOWN: EntityFrameDatum(
                sequence = range(10, 12)
            ),
            DIR_LEFT: EntityFrameDatum(
                sequence = range(12, 15)
            ),
            DIR_SWING_LEFT: EntityFrameDatum(
                sequence = range(16, 19)
            ),
            DIR_SWING_RIGHT: EntityFrameDatum(
                sequence = range(6, 9)
            )
        }

        # Overwrite frame delay
        self.frame_delay = 8

        self.speed = 1.5#0.67
        self.base_speed = self.speed

        # Remember default speed
        self.default_speed = self.speed


        # Specific region in which we can use enemy respawn locations?
        self.respawn_region_name = None


        # Which player (if any) does this enemy prefer to chase?
        self.preferred_target_name = None

        # Which player (if any) is this enemy currently chasing?
        self.current_target_name = None
        self.last_known_target_name = None # To track unique changes, announce to clients on change

        # Flag to track whether or not we want the server
        # to update AI data immediately.
        self.requires_ai_update = False


        # Remember our original coordinates for emergency respawning purposes
        self.ox = self.x
        self.oy = self.y

        # When an enemy respawns, he'll pick a respawn location, but he might
        # have to wait a moment until the coast becomes clear...
        self.respawn_location = (0, 0)

        # Determine how to react to collisions...
        self.food_chain_position = 2


    # Get speed for an Enemy
    def get_speed(self, universe):

        # Scope
        speed = 0


        # Speed with gold?
        if (self.ai_state.ai_is_carrying_gold):

            # Check for cached value
            speed = universe.get_cached_item_attribute_result("enemy-speed:with-gold")

            # No cache value?
            if (speed == None):

                # Calculate modifier
                modifier = (
                    1.0 +
                    sum( o.attributes["gold-pickup-enemy-speed-bonus"] for o in universe.get_equipped_items() if o.is_active() ) +
                    sum( (o.attributes["enemy-speed-modifier"] + o.attributes["enemy-carrying-gold-movement-penalty"]) for o in universe.get_equipped_items() )
                )

                # Calculate final speed
                speed = (modifier * self.speed)

                # Cache new player speed; it will apply until this item's timer expires
                universe.cache_item_attribute_result(
                    "enemy-speed:with-gold",
                    speed
                )

        # No; speed without gold...
        else:

            # Check for cached value
            speed = universe.get_cached_item_attribute_result("enemy-speed")

            # No cache value?
            if (speed == None):

                # Calculate modifier
                modifier = (
                    1.0 +
                    sum( o.attributes["gold-pickup-enemy-speed-bonus"] for o in universe.get_equipped_items() if o.is_active() ) +
                    sum( o.attributes["enemy-speed-modifier"] for o in universe.get_equipped_items() )
                )

                # Calculate final speed
                speed = (modifier * self.speed)

                # Cache new player speed; it will apply until this item's timer expires
                universe.cache_item_attribute_result(
                    "enemy-speed",
                    speed
                )


        # Is the enemy fleeing?
        if (self.ai_state.ai_fright_remaining > 0):

            # What level of the fright skill is the player using?
            level = int( universe.get_session_variable("core.skills.fright").get_value() )

            # Get the stats data for that level of fright from the universe
            stats = universe.get_skill_stats().get_skill_stats_by_level("fright", level)

            # Our final calculation adjusts the flee speed by the given fright level modifier
            flee_speed = speed * stats.get_modifier_by_name("power-factor")

            return flee_speed

        # No; let's return ordinary speed...
        else:

            # On top of the cached speed, let's add in any temporary speed adjustment
            # to compenstate for network lag.  If an enemy falls slightly out of sync,
            # we'll speed up / slow down that enemy to regain sync...
            speed 

            # Return standard speed
            return speed


    def die(self, cause, control_center, universe, with_effects = True, server_approved = False):#, network_controller, universe, p_map, session, with_effects = True, server_approved = False):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # During netplay, only the server can kill an enemy.  Clients must receive explicit instructions from the server to do so...
        if ( (server_approved) or ( network_controller.get_status() != NET_STATUS_CLIENT ) ):

            # The player's inventory might have an item granting enemies bomb immunity
            if ( (cause == DEATH_BY_BOMB) and ( sum( o.attributes["bomb-enemy-immunity"] for o in universe.get_equipped_items() ) > 0 ) ):

                # Enemies are immune to bombs!
                return

            elif (not self.corpsed):

                log( "%s death by %d" % (self.name, cause) )

                # Player inventory can affect respawn wait time
                modifier = (
                    1.0 +
                    sum( o.attributes["enemy-respawn-wait-bonus"] for o in universe.get_equipped_items() )
                )

                self.alive = False
                self.set_status(STATUS_INACTIVE)
                self.ai_state.ai_respawn_interval = int(modifier * AI_ENEMY_RESPAWN_TIME)

                # Use effects?
                if (with_effects):

                    # Particle explosion
                    for j in range(0, 3):
                        for i in range(0, 3):

                            self.particles.append( Particle(self.get_x(), self.get_y(), 0, i, j) )

                if ( network_controller.get_status() != NET_STATUS_CLIENT ):

                    log( "I am server / offline; processing death logic..." )

                    self.handle_death(cause, control_center, universe)#network_controller, universe, p_map, session)


    # Handle an enemy's death
    def handle_death(self, cause, control_center, universe):#network_controller, universe, p_map, session):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # Fetch active map
        m = universe.get_active_map()

        # Also get the map's wave tracker
        wave_tracker = m.get_wave_tracker()


        # Before we get to the fun stuff, let's see if the map defined a special
        # ondeath script for this entity (e.g. npc1.ondeath)
        script_name = "%s.ondeath" % self.name

        if (m.does_script_exist(script_name)):

            m.run_script(script_name, control_center, universe)#, session, universe.quests)


        # The following logic only applies to enemies (not NPCs, which inherit from Enemy class)
        if (self.genus == GENUS_ENEMY):

            # Any time an enemy dies, we keep track another enemy death on this map wave
            wave_tracker.increment_wave_counter("enemy-kills", 1)

            # Also, we want to note how this particular death happened.
            wave_tracker.increment_wave_counter("enemy-kills:%s" % DEATH_TYPE_STRING_NAMES[cause], 1)


            # Check to see if we have a script to run when the player kills an enemy
            if ( m.does_script_exist( wave_tracker.get_wave_param("on-enemy-kill") ) ):

                # Run that script now
                m.run_script(
                    wave_tracker.get_wave_param("on-enemy-kill"),
                    control_center,
                    universe
                )


            # Update universe bad guy kills stat
            universe.get_session_variable("stats.enemies-killed").increment_value(1);


            # Update map param to track another enemy kill
            m.set_param(
                "stats.enemies-killed",
                1 + m.get_param("stats.enemies-killed")
            )


            # Explode upon death?
            chance = sum( o.attributes["enemy-explode-on-death-chance"] for o in universe.equipped_inventory )

            # Any chance?
            if (chance > 0):

                if (random.random() <= chance):

                    # Don't corpse upon explosion!  Let the if (disposable) logic handle that!
                    self.explode(corpse = False, radius = 1, control_center = control_center, universe = universe)


            # Player inventory can allow player to gain free bombs for killing enemies with a bomb
            if (cause == DEATH_BY_BOMB):

                # Count free bombs
                count = sum( o.attributes["bomb-replenishment-adjustment"] for o in universe.get_equipped_items() )

                # Add bombs
                universe.increment_session_variable("core.bombs.count", count)


            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                #universe.net_kill_entity(self, network_controller)
                network_controller.send_entity_die(self, control_center, universe)


            # Execute the "killed-bad-guy" achievement hook
            universe.execute_achievement_hook( "killed-bad-guy", control_center )

            # Is the bad guy "scared" by Fright at the moment?
            if (self.ai_state.ai_fright_remaining > 0):

                # I actually only care if we killed the bad guy with spikes...
                if (cause == DEATH_BY_DEADLY_TILE):

                    # Execute the "killed-scared-bad-guy-with-spikes" achievement hook
                    universe.execute_achievement_hook( "killed-scared-bad-guy-with-spikes", control_center )

        else:
            pass


        if (self.is_disposable):

            self.set_status(STATUS_INACTIVE)

            self.alive = False
            self.corpsed = True # We'll just entirely remove corpsed enemies from the master plane's entity list

            # If this enemy was carrying gold... he's gone forever now!  I could leave the gold "uncollected"
            # to reappear on a revisit, but that's lame.  Let's just give it to the player...
            if (self.ai_state.ai_is_carrying_gold):

                # Fetch the gold (object) they were carrying
                gold = m.get_entity_by_name( self.ai_state.ai_is_carrying_gold_by_name )

                # Validate
                if (gold):

                    # Mark the gold as collected by the local player
                    gold.mark_as_collected_by_actor( control_center, universe, actor = universe.get_local_player() )

                    # Increment gold collected counter for wave (mostly in case we're on a challenge room)
                    wave_tracker.increment_wave_counter("gold", 1);

                    # Flag the enemy as no longer carrying any gold
                    self.ai_state.ai_is_carrying_gold = False
                    self.ai_state.ai_is_carrying_gold_by_name = ""


            # If this wasn't a temporary (e.g. create-random-enemy) entity, then we'll mark the entity
            # down in the obituaries, if the entity has a name...
            if ( (not self.is_ghost) and (self.name != "") ):

                m.record_obituary(self.name, universe)

        else:

            self.respawn()


    def respawn(self):

        # Let's just make sure...
        self.alive = False


        # You can't respawn from corpsedom
        if ( (not self.corpsed) ):

            # No need to render them now...
            self.set_status(STATUS_INACTIVE)

            # Hide them far offscreen
            self.x = -INFINITY
            self.y = -INFINITY

            # Restore original dimensions
            self.width = 24
            self.height = 24

            # No longer frozen
            self.ai_state.ai_frozen = False
            self.ai_state.ai_frozen_for = None

            # No longer trapped
            self.ai_state.ai_is_trapped = False

            self.ai_state.ai_trap_time_remaining = 0

            self.ai_state.ai_trap_exception = None
            self.ai_state.ai_trap_exception_time = 0

            # Wait to respawn...
            self.ai_state.ai_respawn_interval = AI_ENEMY_RESPAWN_TIME


    # Hesitate before moving; flicker a little, a "grace period" as a new level begins before
    # the enemy begins chasing the player.
    def hesitate(self, duration):

        #log2( "Skipping hesitate for debug purposes..." )
        #return

        # (?) Set alive to False
        self.alive = False

        # Set AI state's flash interval (hesitation period)
        self.ai_state.ai_flash_interval = duration


    # Disable all hesitation.  Used only by gifs.
    def no_hesitate(self):

        # Set flash interval to 0
        self.ai_state.ai_flash_interval = 0


    # Get active hesitation value
    def get_hesitation_value(self):

        # Return
        return self.ai_state.ai_flash_interval


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        # Fetch active map
        m = universe.get_active_map()


        # Process gravity
        if ( (self.alive) and (self.status == STATUS_ACTIVE) ):

            # Check for cached gravity calculation
            gravity = universe.get_cached_item_attribute_result("enemy-gravity")

            # No cached value?
            if (gravity == None):

                # Calculate modifier
                modifier = (
                    1.0 +
                    sum( o.attributes["enemy-gravity-bonus"] for o in universe.get_equipped_items() )
                )

                # Calculate value
                gravity = (modifier * RATE_OF_GRAVITY)

                # Cache
                universe.cache_item_attribute_result("enemy-gravity", gravity)

            self.do_gravity(gravity, universe)


        # Did the enemy pick up any gold?  Should we even bother checking?  (Not during certain waves / scenarios!)
        if ( ( self.genus == GENUS_ENEMY ) and ( m.get_wave_tracker().get_wave_param("enemies-collect-gold") == 1 ) and ( not self.ai_state.ai_is_carrying_gold ) and ( not self.ai_state.ai_is_trapped )):

            # Player might have an item that prevents enemies from collecting gold
            if ( sum( o.attributes["enemy-never-carries-gold"] for o in universe.get_equipped_items() ) == 0 ):

                # Did the enemy find any gold?  (This won't return anything for clients during netplay...)
                gold = self.fetch_first_touched_gold(control_center, universe)#network_controller, universe, m, session)

                # If so, he'll grab it...
                if (gold):

                    # The enemy is now carrying gold...
                    self.ai_state.ai_is_carrying_gold = True

                    # Track the name (id) of the gold the enemy grabbed
                    self.ai_state.ai_is_carrying_gold_by_name = gold.name

                    # Disable it on the map
                    gold.mark_as_collected_by_enemy(control_center, universe, enemy = self)#network_controller, universe, m, session, enemy = self)


                    # Check to see if we have a script to run when any enemy collects a piece of gold
                    if ( m.does_script_exist( m.get_wave_tracker().get_wave_param("on-enemy-collect-gold") ) ):

                        # Run that script now
                        m.run_script(
                            m.get_wave_tracker().get_wave_param("on-enemy-collect-gold"),
                            control_center,
                            universe
                        )


        # When alive, check for death...
        if (self.alive):

            # Check for squishing
            if (self.width < 4 or self.height < 4):

                self.queue_death_by_cause(DEATH_BY_PLANAR_SHIFT)

            # Otherwise, check out of bounds...
            else:

                # Fetch active map
                m = universe.get_active_map()


                # If the enemy has gone off of the screen, they must die...
                r = (0, 0, m.width * TILE_WIDTH, m.height * TILE_HEIGHT)

                if ( not intersect( r, self.get_rect() ) ):

                    self.queue_death_by_cause(DEATH_BY_OUT_OF_BOUNDS)


    def process_drama(self, control_center, universe):

        # Process particles
        for particle in self.particles:
            particle.process(None)


        # Remove lost particles
        i = 0

        while (i < len(self.particles)):

            if (self.particles[i].state == False):
                self.particles.pop(i)

            else:
                i += 1


    #def post_process(self, p_map, session = None):
    def post_process(self, control_center, universe):#, network_controller, universe, p_map, session):

        # Queued gold drop command?
        if (self.queued_gold_drop_location):

            # Queued by tile coordinates
            (tx, ty) = self.queued_gold_drop_location

            # Try to find the gold that they're carrying
            gold = universe.get_active_map().get_entity_by_name( self.ai_state.ai_is_carrying_gold_by_name )

            # Validate
            if (gold):

                # Drop the gold!
                self.drop_gold_at_tile_coords(gold, tx, ty, control_center, universe)#network_controller, universe, p_map)


            # No longer carrying gold...
            #self.ai_state.ai_is_carrying_gold = False
            #self.ai_state.ai_is_carrying_gold_by_name = ""


            # Clear queued command
            self.queued_gold_drop_location = None


        # Check for queued death
        if (self.queued_death_by_cause):

            self.die(self.queued_death_by_cause, control_center, universe, with_effects = True)#network_controller, universe, p_map, session, with_effects = True)

            # Reset flag
            self.queued_death_by_cause = None


        elif (self.alive):

            # If we're frozen, see if we can become unfrozen...
            if (self.ai_state.ai_frozen):

                entities = universe.get_active_map().master_plane.query_interentity_collision_for_entity(self).get_results()

                # Coast is clear?
                if (len(entities) == 0):

                    self.ai_state.ai_frozen = False
                    self.ai_state.ai_frozen_for = None

            # Otherwise, we'll see if we can increase our freeze resistance...
            else:

                entities = universe.get_active_map().master_plane.query_interentity_collision_for_entity(self).get_results()

                if (len(entities) == 0):

                    if (self.ai_state.ai_freeze_resistance < AI_MAX_FREEZE_RESISTANCE):

                        # Increase slowly.  It decreases at a faster rate!
                        self.ai_state.ai_freeze_resistance += 1


            # If we have a trap exception and have escaped the trap,
            # we'll slowly drain the timer on that trap exception.
            if (not self.ai_state.ai_is_trapped):

                if (self.ai_state.ai_trap_exception):

                    self.ai_state.ai_trap_exception_time -= 1

                    if (self.ai_state.ai_trap_exception_time <= 0):
                        self.ai_state.ai_trap_exception = None


    def handle_ai(self, control_center, universe):#network_controller, universe, p_map, session):

        # No point in AI for a corpsed enemy
        if (self.corpsed):

            return


        # Not alive at the moment?  We'll need to respawn this enemy...
        elif (not self.alive):

            # Fetch the network controller
            network_controller = control_center.get_network_controller()


            #print "%s not alive..." % self.name

            # Fetch active map
            m = universe.get_active_map()

            if (self.ai_state.ai_respawn_interval > 0):

                # During netplay, only the server can control respawn logic; clients must wait for instructions.
                if ( network_controller.get_status() != NET_STATUS_CLIENT ):

                    self.ai_state.ai_respawn_interval -= 1

                    if (self.ai_state.ai_respawn_interval <= 0):

                        # Get all of the possible respawn locations from the master plane
                        spawns = m.get_entities_by_type(GENUS_RESPAWN_ENEMY)

                        valid_spawn_indices = []

                        # Remove any respawn region that doesn't fall within our respawn region, if applicable...
                        if (self.respawn_region_name):

                            for i in range(0, len(spawns)):

                                if (intersect( m.get_trigger_by_name( self.respawn_region_name ).get_rect(is_editor = False), spawns[i].get_rect() )):

                                    valid_spawn_indices.append(i)

                        else:
                            valid_spawn_indices = range(0, len(spawns))


                        # Only (a) true enemies and (b) NPCs with an explicitly defined respawn region are allowed to use enemy respawn regions
                        if ( (self.genus != GENUS_ENEMY) and (not self.respawn_region_name) ):

                            valid_spawn_indices = []


                        # If some are available...
                        if (len(valid_spawn_indices) > 0):

                            # ... pick one at random
                            index = random.randint(0, len(valid_spawn_indices) - 1)

                            self.respawn_location = (spawns[ valid_spawn_indices[index] ].get_x(), spawns[ valid_spawn_indices[index] ].get_y())

                        # Otherwise, we have to go with our original location...
                        else:

                            self.respawn_location = (self.ox, self.oy)


                        self.x = self.respawn_location[0]
                        self.y = self.respawn_location[1]


                        self.ai_state.ai_flash_interval = AI_ENEMY_FLASH_TIME

            # Flashing?
            elif (self.ai_state.ai_flash_interval > 0):

                self.ai_state.ai_flash_interval -= 1

                # On or off?
                frame = int(self.ai_state.ai_flash_interval / AI_ENEMY_FLASH_DURATION)

                if (frame % 2 == 0):
                    self.set_status(STATUS_INACTIVE)

                else:
                    self.status = STATUS_ACTIVE

            # Now we can try to respawn at the desired location
            else:

                # Fetch active map
                m = universe.get_active_map()

                # Check for any entity intersection...
                available = True

                for genus in (GENUS_PLAYER, GENUS_ENEMY):

                    for entity in m.master_plane.entities[genus]:

                        # There will be no exceptions here.  Spawn or don't.
                        if (self.intersects_entity(entity)):
                            available = False

                # If the respawn location is available, take it...
                if (available):

                    self.status = STATUS_ACTIVE
                    self.alive = True

                    # Restart the cycle
                    self.current_hotspot = 0

                    """ Note - on_respawn does not exist anymore!
                    # Does the entity have a respawn script?
                    #if (self.on_respawn):
                    #    m.event_controller.load_packets_from_xml_node( m.scripts[ self.on_respawn ] )
                    """

                # Otherwise, it's back to flashing some more...
                else:
                    self.ai_state.ai_flash_interval = int(AI_ENEMY_FLASH_TIME / 2)


        # If the enemy is trapped...
        elif (self.ai_state.ai_is_trapped):

            #print "trap time remaining:  ", self.ai_state.ai_trap_time_remaining

            # Fetch active map
            m = universe.get_active_map()

            # If we have trap time remaining...
            if (self.ai_state.ai_trap_time_remaining > 0):

                # Fall all the way into the hole as necessary...
                y_target = (self.ai_state.ai_trap_exception[1] * TILE_HEIGHT)

                # Fall into the darned thing...
                if (self.get_y() < y_target):

                    #print "before:  ", self.y
                    self.move(0, RATE_OF_GRAVITY, universe)
                    #print "after:  ", self.y

                    # Don't overshoot
                    if (self.y > y_target):
                        self.y = y_target

                # Once we've fallen in, we can start to serve our time...
                else:
                    self.ai_state.ai_trap_time_remaining -= 1

            # When we have served our time, we can start to climb out, maybe...
            else:

                y_target = (self.ai_state.ai_trap_exception[1] * TILE_HEIGHT) - TILE_HEIGHT

                # Need to climb out?
                if (self.get_y() > y_target):

                    self.move(0, -RATE_OF_GRAVITY, universe)

                    # Don't overshoot
                    if (self.y < y_target):
                        self.y = y_target

                        #print self.y


                # We've climbed out; we're no longer trapped!
                # Let's set trapped to false and then call ai once more...
                else:
                    self.ai_state.ai_is_trapped = False

                    # Set the occupancy of the tile we escaped to 0...
                    m.master_plane.traps.read( self.ai_state.ai_trap_exception[0], self.ai_state.ai_trap_exception[1] ).set_occupants(0)

                    log( "Fix this code!  set occupants..." )
                    #self.handle_ai(m)

            return


        # Typical AI behavior
        elif (self.ai_state.ai_behavior == AI_BEHAVIOR_NORMAL or (self.ai_state.ai_mood == AI_MOOD_ANGRY) ):

            # Fetch active map
            m = universe.get_active_map()


            # Scope
            player_target = None


            # In single player mode, we will simply try to find the local player.
            if ( control_center.get_network_controller().get_status() == NET_STATUS_OFFLINE ):

                # Find local player
                player_target = universe.get_local_player()

            # In cooperative mode, the client will try to find the preferred
            # target, but will make no changes if it does not exist.
            elif ( control_center.get_network_controller().get_status() == NET_STATUS_CLIENT ):

                # Try to find the current target by name
                player_target = m.get_entity_by_name(self.current_target_name)

            # In cooperative mode, the server will find the preferred target,
            # but then also update the target if the preferred target does
            # not exist, or if the preferred target is dead.
            elif ( control_center.get_network_controller().get_status() == NET_STATUS_SERVER ):

                # Let's try to find the preferred player target for this enemy.
                # If we don't find it, we'll look for the next player target until
                # we find a viable "current" target.
                player_target = m.get_entity_by_name(self.preferred_target_name)

                # If we didn't find that entity (or it isn't alive), we'll end up defaulting to the first available player entity...
                if ( (not player_target) or (player_target.get_status() == STATUS_INACTIVE) or ( not player_target.is_touchable() ) ):

                    # Reset player target to null, as we either cannot find the preferred target,
                    # or the preferred target is not in the game at the moment.
                    player_target = None


                    # Grab all available player entities
                    active_player_entities = m.get_active_entities_by_type(GENUS_PLAYER)

                    # Surely we at least found one?  Maybe?
                    for entity in active_player_entities:

                        # Take the first living player entity
                        if (not player_target):

                            # Can we go after this player?
                            if ( ( entity.get_status() == STATUS_ACTIVE ) and ( entity.is_touchable() ) ):

                                player_target = entity

                # If we have a valid player target, then update the current target's name.
                if (player_target):

                    # Update current name
                    self.set_current_target_name(player_target.name, control_center, universe)



            # Validate that we found a player target
            if (player_target):

                # Update primary color to match preferred target
                self.primary_color = player_target.primary_color

                # Enemies in single player do not alter their color
                if ( control_center.get_network_controller().get_status() == NET_STATUS_OFFLINE ):

                    # Stay full color
                    self.primary_color = (255, 255, 255)


                # As long as that player isn't invisible, then track them fresh...
                if (not player_target.is_invisible):

                    (x, y) = (
                        (player_target.get_x() / TILE_WIDTH) * TILE_WIDTH,
                        (player_target.get_y() / TILE_HEIGHT) * TILE_HEIGHT
                    )

                    self.ai_state.ai_last_known_position = (x, y)


                    # If the player has sent out a hologram, the enemy will want to chase that hologram instead... irresistable...
                    hologram = m.get_entity_by_name("%s.hologram" % player_target.name)#"player1.hologram")

                    # See if we found a hologram for the player target...
                    if (hologram):

                        self.ai_state.ai_last_known_position = (
                            (hologram.get_x() / TILE_WIDTH) * TILE_WIDTH,
                            (hologram.get_y() / TILE_HEIGHT) * TILE_HEIGHT
                        )


            if (self.can_move and (not self.ai_state.ai_frozen)):

                # How quickly will they seek / flee?
                speed = self.get_speed(universe)

                # Defaults
                (speed_x, speed_y) = (speed, speed)

                #print speed, self.ai_state
                #print self.ai_state.ai_last_known_position
                # Check to see if we have a target
                if (self.ai_state.ai_last_known_position != None):

                    # Mirror for each axis, adjusting for known latency
                    (speed_x, speed_y) = self.adjust_speed_for_latency(speed_x, speed_y, self.ai_state.ai_last_known_position[0], self.ai_state.ai_last_known_position[1])


                # Typically we seek a target...
                if (self.ai_state.ai_fright_remaining <= 0 and (self.ai_state.ai_last_known_position != None) ):

                    self.seek_location(self.ai_state.ai_last_known_position[0], self.ai_state.ai_last_known_position[1], vx = speed_x, vy = speed_y, universe = universe)

                # Sometimes, though, the enemies get scared...
                elif (self.ai_state.ai_last_known_position != None):

                    # Avoid the player...
                    self.avoid_location(self.ai_state.ai_last_known_position[0], self.ai_state.ai_last_known_position[1], vx = speed_x, vy = speed_y, universe = universe)

                    # Less afraid over time...
                    self.ai_state.ai_fright_remaining -= 1


        # Patrolling enemies follow a set route until they see the enemy ahead of them...
        elif (self.ai_state.ai_behavior == AI_BEHAVIOR_PATROLLING):

            #print self.name, " is patrolling, seeking hotspot %d" % self.current_hotspot

            # Fetch active map
            m = universe.get_active_map()


            # Check to see if we can make eye contact with the player(s)
            if (self.genus == GENUS_ENEMY):

                for entity in m.master_plane.entities[GENUS_PLAYER]:

                    # First an eye level test
                    (my_ty, e_ty) = (
                        int( self.get_y() / TILE_HEIGHT ),
                        int( entity.get_y() / TILE_HEIGHT )
                    )

                    # So far, so good...
                    if (my_ty == e_ty):

                        # Now make sure we're facing them... let's check left first...
                        if ( (entity.get_x() < self.get_x()) and (self.ai_state.last_lateral_move == DIR_LEFT) ):

                            # Now we just have to check for choke points...
                            (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y(), allow_fall = True) # We can see across chasms...

                            # Get the tx of the player entity...
                            e_tx = int( entity.get_x() / TILE_WIDTH )

                            # Is it within the choke points?
                            if (e_tx > tx1):

                                # Angry!
                                self.ai_state.ai_mood = AI_MOOD_ANGRY
                                log( "ANGRY LEFT!" )

                        # Nah, check right...
                        elif ( (entity.get_x() > self.get_x()) and (self.ai_state.last_lateral_move == DIR_RIGHT) ):

                            # Check the choke points...
                            (tx1, tx2) = m.master_plane.get_choke_points_in_tile_coords(self.get_x(), self.get_y(), allow_fall = True) # We can see across chasms...

                            # Player tx
                            e_tx = int( entity.get_x() / TILE_WIDTH )

                            # Bounds check
                            if (e_tx < tx2):

                                # Become very angry
                                self.ai_state.ai_mood = AI_MOOD_ANGRY
                                log( "ANGRY RIGHT!" )


            # Now let's check the patrol hotspots
            if (len(self.hotspots) > 0):

                (x, y) = (
                    m.get_trigger_by_name( self.hotspots[self.current_hotspot] ).x * TILE_WIDTH,
                    m.get_trigger_by_name( self.hotspots[self.current_hotspot] ).y * TILE_HEIGHT
                )

                #print "seeking:  (%s, %s)" % (x, y)


                if (self.can_move and (not self.ai_state.ai_frozen)):

                    # Do we need to wait for a patrol delay?
                    if (self.patrol_delay > 0):

                        # Wait...
                        self.patrol_delay -= 1

                    else:

                        # Get speed
                        speed = self.get_speed(universe)

                        # Seek the hotspot
                        self.seek_location(x, y, vx = speed, vy = speed, universe = universe)


                # Upon reaching the location, proceed to the next hotspot
                if (self.get_x() == x and self.get_y() == y):

                    # Perfect alignment
                    self.x = x
                    self.y = y

                    self.current_hotspot += 1

                    if (self.current_hotspot >= len(self.hotspots)):
                        self.current_hotspot = 0

                    # We can hack in "delays" between hotspots.  It's super hacky.
                    while ( self.hotspots[self.current_hotspot].startswith("sleep(") ):

                        # Retrieve param
                        param = self.hotspots[self.current_hotspot].replace("sleep", "").replace("(", "").replace(")", "")

                        # Validate that it's numeric
                        if ( is_numeric(param) ):

                            # Add to patrol delay.  Parse param as float, then apply in seconds
                            self.patrol_delay += int( float(param) * 60 ) # 60fps **hard-coded

                        # Move to the next hotspot (this one isn't a hotspot, it's a sleep command)
                        self.current_hotspot += 1

                        # Wrap if necessary
                        if ( self.current_hotspot >= len(self.hotspots) ):

                            # Clamp
                            self.current_hotspot = 0


        # Territorial enemies will follow their hotspots unless you invade their territory.
        # At that point, they will become more aggressive.
        elif (self.ai_state.ai_behavior == AI_BEHAVIOR_TERRITORIAL):

            # Fetch active map
            m = universe.get_active_map()


            # Check for territory intrusion
            if (self.ai_state.ai_territory):

                t = m.get_trigger_by_name(self.ai_state.ai_territory)
                r = (t.x * TILE_WIDTH, t.y * TILE_HEIGHT, t.width * TILE_WIDTH, t.height * TILE_HEIGHT)

                # Invasion?
                if (intersect(self.get_rect(), r)):

                    # The enemy will now chase the player persistently
                    self.ai_state.ai_mood = AI_MOOD_ANGRY


            # Now check hotspots...
            if (len(self.hotspots) > 0):

                (x, y) = (
                    m.get_trigger_by_name( self.hotspots[self.current_hotspot] ).x * TILE_WIDTH,
                    m.get_trigger_by_name( self.hotspots[self.current_hotspot] ).y * TILE_HEIGHT
                )


                if (self.can_move and (not self.ai_state.ai_frozen)):

                    speed = self.get_speed(universe)

                    self.seek_location(x, y, vx = speed, vy = speed, universe = universe)


                # Upon reaching the location, proceed to the next hotspot
                if (self.get_x() == x and self.get_y() == y):

                    # Perfect alignment
                    self.x = x
                    self.y = y

                    self.current_hotspot += 1

                    if (self.current_hotspot >= len(self.hotspots)):
                        self.current_hotspot = 0

    def animate(self):

        self.frame_interval -= 1

        if (self.frame_interval <= 0):

            # Reset delay
            self.frame_interval = self.frame_delay

            # Animate
            self.frame += 1

            if ( self.frame >= self.frame_indices[self.direction].get_sequence_length() ):
                self.frame = 0


    def render(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        if (self.status == STATUS_ACTIVE):

            if ( (is_editor) or (not self.editor_only) ):

                # Assume walking / climbing
                frame = self.frame_indices[self.direction].get_frame_at_sequence_index(self.frame)

                # Check for monkey bar swinging...
                if (self.is_swinging):

                    if (self.direction == DIR_LEFT):
                        frame = self.frame_indices[DIR_SWING_LEFT].get_frame_at_sequence_index(self.frame)

                    elif (self.direction == DIR_RIGHT):
                        frame = self.frame_indices[DIR_SWING_RIGHT].get_frame_at_sequence_index(self.frame)

                # Carrying gold?
                if (self.ai_state.ai_is_carrying_gold):

                    # Render a somewhat gold-looking color (hard-coded color)
                    window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, scale = scale, frame = frame, gl_color = (1.0, 0.75, 0.15, 0.75 * gl_color[3]))

                else:

                    # If the enemy is trapped, then we'll make him flicker a bit when he's about to get out
                    if ( (self.ai_state.ai_trap_time_remaining > 0) and (self.ai_state.ai_trap_time_remaining < AI_ENEMY_TRAP_ESCAPE_WARNING_PERIOD_LENGTH) ):

                        # On or off?
                        frame_flicker = ( int(self.ai_state.ai_trap_time_remaining / AI_ENEMY_TRAP_ESCAPE_FLASH_DURATION) % 2 == 0 )

                        if (frame_flicker):

                            (dx, dy) = (
                                random.randint(-2, 2),
                                0
                            )

                            # Render at 50% opacity (a "flicker" effect, in theory)
                            window_controller.get_gfx_controller().draw_sprite(sx + self.get_x() + dx, sy + self.get_y() + dy, self.width, self.height, sprite, scale = scale, frame = frame, gl_color = (gl_color[0], gl_color[1], gl_color[2], 0.5 * gl_color[3]))

                        else:

                            # Render normally
                            window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, scale = scale, frame = frame, gl_color = gl_color)

                    # He's either not stuck, or recently stuck and nowhere close to climbing out...
                    else:

                        # Render normally
                        window_controller.get_gfx_controller().draw_sprite( sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, scale = scale, frame = frame, gl_color = rgb_to_glcolor( set_alpha_for_rgb(gl_color[3], self.primary_color) ) )


                # Scared?
                if (self.ai_state.ai_fright_remaining > 0):

                    # Render a red color (hard-coded color)
                    window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, scale = scale, frame = frame, gl_color = (1.0, 0.0, 0.0, 0.5 * gl_color[3]))

        # Render particles
        for particle in self.particles:
            particle.render(sx, sy, sprite, window_controller)


class EnemyRespawn(Entity):

    def __init__(self):

        Entity.__init__(self)

        self.genus = GENUS_RESPAWN_ENEMY
        self.species = None

        self.editor_only = True

        # No need to track this across sessions, it's a static respawn object
        self.is_ghost = True

    def process(self, control_center, universe):#, network_controller, universe, p_map, session):
        return

class NPC(Enemy):

    def __init__(self):

        Enemy.__init__(self)

        self.genus = GENUS_NPC
        self.species = "generic"


        # This is important!
        # All NPCs are disposable.  This means that once they die, they never come back.
        self.is_disposable = True

        # By default, let's set all NPC characters to class "npc."  If level file explicitly defines it, we'll totally overwrite this default.
        self.set_class("npc")


        # NPCs are kind of slow
        self.speed = 0.85# + 1.0# + 5.0
        self.base_speed = self.speed

        # Remember the default speed in case we want to revert
        self.default_speed = self.speed


        self.frame = 0


        # An NPC can have various conversation branches.  Each branch will hold a set of linear
        # dialogue lines; the NPC will cycle through those branches linearly.  After exhausting
        # the linear options, the NPC will randomly cycle through a variety of "nag" messages.
        #
        # The exception to this involves one linear line's eventual outcome blacklisting / whitelisting
        # a subsequent line.
        self.conversations = {}

        # At times, we'll want to render an indicator above an NPC,
        # such as an explanation mark for a new quest.
        self.indicators = {
            "quest-available": False,
            "quest-complete": False,
            "target": False,
            "merchant": False
        }


        # Some NPCs will be merchants.  When you first shop with them, they will populate
        # an "inventory" of items to sell.  The parameters (quality, source, etc.) are defined
        # within the level menu (shopping menu).
        self.inventory = []

        # Track whether we've initiated an inventory
        self.initiated_inventory = False

        # How many items has this NPC sold to the player?
        self.sales_count = 0

        # An NPC will deal from a certain set of "warehouses."
        # This determines where she / he can or cannot get items from.
        self.warehouses = []


    def configure(self, options):

        # By default, an NPC will engage in simple patrolling behavior
        self.ai_state.ai_behavior = AI_BEHAVIOR_PATROLLING


        # Check NPC-specific attributes (mount and position)
        if ( "species" in options ):
            self.species = options["species"]


        # For chaining
        return self


    def load_conversation_data_from_node(self, node):

        # Global node
        ref_characters = node.get_first_node_by_tag("characters")

        if (ref_characters):

            # Find any data for this npc...
            ref_npc = ref_characters.get_first_node_by_tag(self.name)

            if (ref_npc):

                # Get the relevant chapter data
                ref_chapter = ref_npc.get_first_node_by_tag("chapter1")

                if (ref_chapter):

                    # Load in any conversation associated with this NPC in this chapter...
                    conversation_collection = ref_chapter.get_nodes_by_tag("conversation")

                    for ref_conversation in conversation_collection:

                        # Import
                        self.import_conversation_from_node(ref_conversation)


    # Perform the task of importing a conversation from a given xml node
    def import_conversation_from_node(self, node):

        # Don't overwrite existing conversations
        if ( not ( node.get_attribute("id") in self.conversations ) ):

            # Key by conversation id (e.g. "offering-quest")
            self.conversations[ node.get_attribute("id") ] = Conversation().import_conversation_data_from_node(node)


            # Sometimes a conversation will have a nested conversation.  This will not go beyond a single level
            # of nesting, so I'm not going to bother with recursion right now.
            child_conversation_collection = node.get_nodes_by_tag("conversation")

            for ref_child_conversation in child_conversation_collection:

                self.conversations[ ref_child_conversation.get_attribute("id") ] = Conversation().import_conversation_data_from_node( ref_child_conversation )


    # NPCs need a special xml string
    def compile_xml_string(self, prefix = ""):

        xml = "%s<entity " % prefix

        xml += "x = '%d' y = '%d' genus = '%d' species = '%s' ai-behavior = '%d' name = '%s' class = '%s' nick = '%s' title = '%s' />\n" % ( int(self.get_x() / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT), self.genus, self.species, self.ai_state.ai_behavior, self.name.replace("'", "&apos;"), xml_encode(self.class_name), self.nick.replace("'", "&apos;"), self.title.replace("'", "&apos;"))

        return xml


    # The NPC has some special state data (they might have an inventory, etc.)
    def save_state(self):

        # Start with common data
        root = Entity.save_state(self)


        # Add a node for indicator data
        node = root.add_node(
            XMLNode("indicators")
        )

        # Loop indicator types
        for key in self.indicators:

            # Add indicator state
            node.add_node(
                XMLNode("indicator").set_attributes({
                    "name": xml_encode( "%s" % key ),
                    "active": xml_encode( "%d" % int( self.indicators[key] ) )
                })
            )


        # Do we need to track an inventory?
        if (self.initiated_inventory):

            # Create a node for inventory data
            node = root.add_node(
                XMLNode("inventory")
            )

            # I guess we're keeping sales count as an attribute
            node.set_attributes({
                "sales-count": xml_encode( "%d" % self.sales_count )
            })

            # Loop inventory
            for item_name in self.inventory:

                # Add node for item
                node.add_node(
                    XMLNode("item").set_attributes({
                        "name": xml_encode( "%s" % item_name )
                    })
                )


        # Return node
        return root


    # The NPC will need a special recall function as well (for inventory, etc.)
    def load_state(self, node):

        # Load base data
        Entity.load_state(self, node)


        # Can we find any indicator data to load?
        ref_indicators = node.find_node_by_tag("indicators")

        # Validate
        if (ref_indicators):

            # Loop all
            for ref_indicator in ref_indicators.get_nodes_by_tag("indicator"):

                # Get name and given value
                (name, value) = (
                    ref_indicator.get_attribute("name"),
                    ref_indicator.get_attribute("active")
                )

                # Validate indicator name
                if (name in self.indicators):

                    # Set value
                    self.indicators[name] = (value == "1")



        # Can we find any inventory data to load?
        ref_inventory = node.get_first_node_by_tag("inventory")

        if (ref_inventory):

            # Grab the sales count...
            self.sales_count = int( ref_inventory.get_attribute("sales-count") )

            # Now populate the inventory...
            item_name_collection = ref_inventory.get_nodes_by_tag("item")

            for ref_item_name in item_name_collection:

                self.inventory.append( ref_item_name.get_attribute("name") )


    # When an NPC dies, we will run all of the base Enemy class logic.
    # After that, though, we're also going to automatically enter an obituary into the historical record for this NPC.
    def handle_death(self, cause, control_center, universe):

        # First, run global npc.ondeath script
        universe.run_script("npc.ondeath", control_center)

        # If this NPC happened to work as a merchant, run the merchant ondeath as well
        if ( self.has_class("merchant") ):

            # Run global script
            universe.run_script("merchant.ondeath", control_center)


        # Run base logic
        Enemy.handle_death(self, cause, control_center, universe)


        # Special hacked-in achievement hook
        if (cause == DEATH_BY_PLANAR_SHIFT):

            # Currently I'm only coding this one special case
            universe.execute_achievement_hook( "killed-npc-by-planar-shift", control_center )


        # We're going to do this automatically instead of doing it
        # manually every time in the ondeath script events.  Easier this way!
        universe.add_historical_record(
            "obituary",
            "%s/%s" % (universe.get_active_map().get_name(), self.name)
        )

        # Execute the "killed-npc" achievement hook
        universe.execute_achievement_hook( "killed-npc", control_center )


    def get_conversation_by_id(self, conversation_id):

        # Validate
        if (conversation_id in self.conversations):

            return self.conversations[conversation_id]

        # Sorry, we couldn't find it...
        else:

            return None


    def set_conversation_line_status(self, conversation_id, line_id, active):

        log( conversation_id, line_id, active )

        for key in self.conversations[conversation_id].branches:

            branch = self.conversations[conversation_id].branches[key]

            for line in branch.linear_data:

                if (line.id == line_id):

                    line.active = active

            for line in branch.nag_data:

                if (line.id == line_id):

                    line.active = active


    # Set status on lines in a given conversation with a given class
    def update_conversation_lines_by_class(self, conversation_id, class_name, enabled = None):

        # Validate conversation id
        if (conversation_id in self.conversations):

            # Update enabled status?
            if (enabled != None):

                # Loop lines matching class
                for line in self.conversations[conversation_id].get_lines_by_class(class_name):

                    # Update enabled status
                    line.set_enabled(enabled)


    # Enable lines in a given conversation with a given class
    def enable_conversation_lines_by_class(self, conversation_id, class_name):

        # Enable all matching lines
        self.update_conversation_lines_by_class(conversation_id, class_name, enabled = True)


    # Disable lines in a given conversation with a given class
    def disable_conversation_lines_by_class(self, conversation_id, class_name):

        # Disable all matching lines
        self.update_conversation_lines_by_class(conversation_id, class_name, enabled = False)


    # Set an NPC indicator to a given status
    def set_indicator(self, key, value):

        # Validate
        if (key in self.indicators):

            # Update
            self.indicators[key] = value


    # Clear all indicators
    def clear_indicators(self):

        # Loop each indicator
        for key in self.indicators:

            # Reset
            self.indicators[key] = False


    # An NPC can talk to the player.
    # This function accepts the conversation to use and which way to render the conversation (standard, shop, fyi, etc.)
    def talk(self, conversation_id, style, control_center, universe):

        #print "npc talk - '%s'" % conversation_id
        #print "\tnpc talk - conversations - %s" % " ".join(self.conversations.keys())

        # Precalculate talk menu id (based on this NPC's name)
        menu_id = "npc-%s-talk" % self.get_name()


        # Check for a menu (within the MenuController) belonging to this NPC.
        # If this NPC is already talking, then the next talk script command must wait.
        if ( control_center.get_menu_controller().get_menu_by_id(menu_id) ):
            logn( "entity npc talk", "%s exists (busy)...\n" % menu_id)

            # Return False to indicate that we're already running another conversation.
            # Try again later...
            return False

        # Validate conversation
        elif (conversation_id in self.conversations):

            # When beginning a conversation, we always start at the root.
            # So, yes, right now this is just hard-coded (branches["root"]).
            if ( "root" in self.conversations[conversation_id].branches ):

                line = self.conversations[conversation_id].branches["root"].get_next_line()

                # Validate
                if (line):

                    # Fetch the widget dispatcher;
                    widget_dispatcher = control_center.get_widget_dispatcher()

                    # and the menu controller;
                    menu_controller = control_center.get_menu_controller()

                    # and the splash controller
                    splash_controller = control_center.get_splash_controller()


                    # Create a shopping dialogue panel?
                    if (style == "shop"):#event_type == eventtypes.DIALOGUE_SHOP):

                        # Pause game action
                        universe.pause()

                        # Call for a pause splash
                        splash_controller.set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)

                        # Add a "shopping" dialogue panel (configured to look identical with a real shop menu for visual consistency
                        # when we switch to a real shop menu).
                        menu_controller.add(
                            widget_dispatcher.create_shopping_dialogue_panel().configure({
                                "id": menu_id,
                                "narrator": self,
                                "conversation-id": conversation_id,
                                "redirect": line.redirect,
                                "source-node": line
                            })
                        )


                    # FYI dialogue panel (narrate cutscenes, etc., does not respond at all to user input)
                    # Includes a hacked-in id "parameter"
                    elif ( style.startswith("fyi:") ):# == "fyi"):#event_type == eventtypes.DIALOGUE_FYI):

                        # Parse out the given dialogue panel id
                        panel_id = style.replace("fyi:", "")

                        # Add an "FYI" dialogue panel.
                        # Note that FYI dialogue panels come with an explicit id, unlike other dialogue panel types.
                        menu_controller.add(
                            widget_dispatcher.create_fyi_dialogue_panel().configure({
                                "id": panel_id,
                                "narrator": self,
                                "conversation-id": conversation_id,
                                "redirect": line.redirect,
                                "source-node": line
                            })
                        )


                    # Nope, just an ordinary dialogue panel...
                    else:

                        # Pause the action
                        universe.pause()

                        # Summon the pause splash
                        splash_controller.set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)

                        # Add a standard / generic dialogue widget
                        menu_controller.add(
                            widget_dispatcher.create_generic_dialogue_panel().configure({
                                "id": menu_id,
                                "narrator": self,
                                "conversation-id": conversation_id,
                                "redirect": line.redirect,
                                "source-node": line
                            })
                        )

            else:
                logn( "conversation debug", "Warning:  Conversation 'root' does not exist." )


        # Default to "done"
        return True


    # Clear all warehouses, probably to redefine warehouse listing
    def clear_warehouses(self):

        # Clear
        self.warehouses = []

        # Done
        return True


    # Add a new warehouse that the NPC can carry inventory from, by name
    def add_warehouse(self, name):

        # New warehouse available!
        self.warehouses.append(name)

        # Done
        return True


    # When we shop with an NPC, we make sure to populate their vendor inventory
    # according to the shopping menu's specs.  max_items defines how many items
    # they can stock at a given time; max_reloads defines how many times they can
    # bring in a new item (to replace one they have sold).
    def populate_vendor_inventory(self, min_quality, max_quality, required_item_names, max_items, max_reloads, universe):

        # First, establish that we're tending to the inventory
        self.initiated_inventory = True


        # Do we need to include any required item?
        for item_name in required_item_names:

            # Attempt to add the item to the inventory.  (Function checks for previous acquisition / duplicate listings, prevents them.)
            self.add_item_to_vendor_inventory(item_name, universe)


        # Let's calculate how many new items we might need to add...
        free_slots = (max_items + max_reloads) - (len(self.inventory) + self.sales_count)

        # Constrain free_slots to 0 - max_items
        if (free_slots < 0):
            free_slots = 0

        elif ( (free_slots + len(self.inventory)) > max_items):
            free_slots = max_items - len(self.inventory)


        # Get as many possible items at random, according to the warehouses this NPC has access to
        # and the specified min/max quality parameters...
        self.inventory.extend(
            universe.fetch_n_virgin_item_names(n = free_slots, min_quality = min_quality, max_quality = max_quality, warehouse_collection = self.warehouses, blacklist = self.inventory)
        )


    def remove_erstwhile_acquired_items_from_inventory(self, universe):

        i = 0

        while (i < len(self.inventory)):

            # If the player has found this item since they last shopped, then
            # we should clear it from the vendor inventory now.
            if (universe.is_item_acquired(self.inventory[i])):

                self.inventory.pop(i)

            else:
                i += 1


    # Add an item to this NPC's inventory, by name
    def add_item_to_vendor_inventory(self, item_name, universe):

        # Don't duplicate inventory listings...
        if (not (item_name in self.inventory)):

            # If the player already has this item, don't list it...
            if ( not universe.is_item_acquired(item_name) ):

                # Validate that the item exists.  Retrieve the item from the core universe item stash. 
                item = universe.get_item_by_name(item_name)

                # Validate
                if (item):

                    # Add the item name as a prize option...
                    self.inventory.append(item_name)


    # Remove an item from this NPC's inventory, by name
    def remove_item_from_vendor_inventory(self, item_name):

        i = 0

        while (i < len(self.inventory)):

            if (self.inventory[i] == item_name):

                self.inventory.pop(i)

            else:
                i += 1


    # Reset / clear this vendor's inventory
    def clear_vendor_inventory(self):

        self.inventory = []


    def increase_sales_count(self, amount):

        self.sales_count += amount


    # Count the number of item's in the vendor's active inventory
    def get_vendor_inventory_count(self):

        return len(self.inventory)


    """
    # Count the number of remaining items the vendor could potentially sell to the player (current inventory + reloads available)
    def get_vendor_potential_inventory_count(self):

        # Combine current inventory size with remaining reloads
        return ( len(self.inventory) + 
        # I have no direct access to reloads data, abandoning function for now...
    """


    def get_vendor_inventory_item_names(self):

        return self.inventory


    def get_vendor_inventory_items_as_nodes(self, universe):

        # Add every item in the active inventory...
        for item_name in self.inventory:

            # Handle to the item itself
            item = universe.get_item_by_name(item_name)

            # Build markup
            markup = ""


            # Can the player afford this item?
            if ( int(universe.session["core.gold.wallet"]["value"]) >= item.cost ):

                markup = """
                    <item glow = '1' disabled = '0' render-border = '0' extra-padding = '-5'>
                        <contents>
                            <icon x = '5%' y = '5' index = '28' display = 'on-focus' position = 'absolute' />
                            <label x = '17%' y = '5' width = '90%' value = '#ITEM-TITLE
[color=dim]Cost:  [color=evil]#ITEM-COST[/color] gold[/color]' />
                            <action do = 'buy-item' -item-name = '#ITEM-NAME' />
                        </contents>
                        <tooltip>
                            <item>
                                <icon x = '0' y = '0' index = '13' />
                                <label x = '12%' y = '0' width = '75%' value = '[color=special]Item Details:[/color]' />
                                <label x = '12%' y = '40' width = '88%' value = '#ITEM-ADVERTISEMENT' />
                            </item>
                        </tooltip>
                    </item>
                """

            # No?  Dim it and list it as too expensive...
            else:

                markup = """
                        <item glow = '1' disabled = '0' render-border = '0' extra-padding = '-5'>
                            <contents>
                                <icon x = '5%' y = '5' index = '28' display = 'on-focus' position = 'absolute' />
                                <label x = '17%' y = '5' width = '90%' value = '[color=dim]#ITEM-TITLE[/color]
[color=dim]Cost:  [color=warning]#ITEM-COST[/color] gold[/color]' />
                                <action do = 'nothing' -item-name = '#ITEM-NAME' />
                            </contents>
                            <tooltip>
                                <item>
                                    <icon x = '0' y = '0' index = '13' />
                                    <label x = '12%' y = '0' width = '75%' value = '[color=special]Item Details:[/color]' />
                                    <label x = '12%' y = '40' width = '88%' value = '#ITEM-ADVERTISEMENT

[color=warning]You do not have enough gold to buy this item.[/color]' />
                                </item>
                            </tooltip>
                        </item>
                """

            # Handle translations
            translations = {
                "#ITEM-NAME": xml_encode(item.name),
                "#ITEM-TITLE": xml_encode(item.title),
                "#ITEM-ADVERTISEMENT": xml_encode(item.description),
                "#ITEM-COST": xml_encode("%d" % item.cost)
            }


            for key in translations:
                markup = markup.replace(key, translations[key])

            xml += markup


        # Lastly, a back button...
        xml += """
            <item glow = '1' disabled = '0' render-border = '0' extra-padding = '-5'>
                <icon x = '5%' y = '5' index = '28' display = 'on-focus' position = 'absolute' />
                <label x = '17%' y = '5' width = '90%' value = 'Leave Shop
[color=dim]Buy Nothing[/color]' />
                <action do = 'back' -item-name = 'n/a' />
            </item>
        """


        return xml


    # Shop with an NPC
    def shop(self, settings, control_center, universe):

        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the menu controller;
        menu_controller = control_center.get_menu_controller()

        # and the splash controller
        splash_controller = control_center.get_splash_controller()



        # Inject NPC vendor into settings hash.  **HACK of a sort...
        settings["vendor"] = self


        # Add a Shopping Menu
        menu_controller.add(
            widget_dispatcher.create_shop_menu().configure(
                settings
            )
        )
        log2( "Now we're shopping... game should remain paused" )



        # Only mark this event as completed when the shop menu has faded away (user has bought something or cancelled the menu)
        return True#(not m.is_busy())


    def render(self, sx, sy, sprites, scale, is_editor, gl_color, window_controller = None):

        if ( (self.status == STATUS_ACTIVE) and (self.alive) ):

            if ( (is_editor) or (not self.editor_only) ):

                # Assume walking / climbing
                frame = self.frame_indices[self.direction].get_frame_at_sequence_index(self.frame)

                # Check for monkey bar swinging...
                if (self.is_swinging):

                    if (self.direction == DIR_LEFT):
                        frame = self.frame_indices[DIR_SWING_LEFT].get_frame_at_sequence_index(self.frame)

                    elif (self.direction == DIR_RIGHT):
                        frame = self.frame_indices[DIR_SWING_RIGHT].get_frame_at_sequence_index(self.frame)


                # Render sprite
                window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprites[self.species], scale = scale, gl_color = gl_color, frame = frame)

                # Render name above NPC, because they all look the same...
                window_controller.get_default_text_controller().get_text_renderer().render_with_wrap(self.nick, sx + self.get_x() + int(self.width / 2), sy + self.get_y() - 20, (225, 225, 225), align = "center")


                # Render particles
                for particle in self.particles:
                    particle.render(sx, sy, sprites[self.species], window_controller)


                # Build an indicator string.  Typically just one character (e.g. exclamation point).
                indicator_string = ""


                # Merchant?
                if (self.indicators["merchant"]):

                    indicator_string += "[color=lightblue]$[/color]"


                # Quest available?
                if (self.indicators["quest-available"]):

                    indicator_string += "[color=yellow]?[/color]"

                # Quest complete?
                elif (self.indicators["quest-complete"]):

                    indicator_string += "[color=green]![/color]"


                # Quest target?  (i.e. kill this NPC)
                if (self.indicators["target"]):

                    indicator_string += "[color=red]x[/color]"


                if ( len(indicator_string) > 0 ):

                    # Hard-coded color classes
                    color_classes = {
                        "lightblue": (37, 135, 255),
                        "yellow": (225, 225, 25),
                        "green": (25, 225, 25),
                        "red": (225, 25, 25)
                    }

                    window_controller.get_default_text_controller().get_text_renderer().render_with_wrap(indicator_string, sx + self.get_x() + int(self.width / 2), sy + self.get_y() - 35, (225, 225, 225), align = "center", color_classes = color_classes)


        # Yellow exclamation mark indicates available quest
        #window_controller.get_default_text_controller().get_text_renderer().render("!", sx + self.get_x() + int(self.width / 2), sy + self.get_y() - 20, (225, 225, 25), p_align = "center")

        # Some other color of something indicates merchant status... + sign?

        # Render particles
        for particle in self.particles:
            particle.render(sx, sy, sprites[self.species], window_controller)


# A hologram is an NPC that always moves in a set direction.
class Hologram(NPC, ExplodingEntityExt, GoldCollectorEntityExt):

    def __init__(self, name = "", author = None, direction = 0, lifespan = 0, exploding = False, collecting = False, xml = None):

        NPC.__init__(self)
        ExplodingEntityExt.__init__(self)
        GoldCollectorEntityExt.__init__(self)

        self.genus = GENUS_HOLOGRAM

        # Don't record this entity for map memory
        self.is_ghost = True


        # Track name
        self.name = name

        # Which entity spawned this hologram?  (player1 entity, maybe?  etc.)
        self.author = author

        # Which direction to move?
        self.direction = direction


        # Lifespan
        self.lifespan = lifespan

        # Explode upon hitting a wall?
        self.exploding = exploding

        # Pick up gold along the way?
        self.collecting = collecting


        # Faster than a regular NPC
        self.speed = 1.65
        self.base_speed = self.speed

        # Remember default speed, although I don't foresee ever changing a hologram's speed, at this point
        self.default_speed = self.speed


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        # Process particles, always...
        for particle in self.particles:
            particle.process(None)


        # Can this hologram collect gold?
        if (self.collecting):

            # Check for gold!
            entity = self.fetch_first_touched_gold(control_center, universe)

            # Did the hologram find any gold?  If so, collect it...
            if (entity):

                entity.mark_as_collected_by_actor(control_center, universe, actor = self.author)


        # Check lifespan
        self.lifespan -= 1


        # Out of lifespan?
        if (self.lifespan <= 0):

            self.expire()

        # No; let's move along...
        else:

            # Fetch active map
            m = universe.get_active_map()

            # Check gravity
            self.do_gravity(RATE_OF_GRAVITY, universe)


    def expire(self):

        self.set_status(STATUS_INACTIVE)
        self.alive = False

        self.corpsed = True


    def handle_ai(self, control_center, universe):#, network_controller, universe, p_map, session):

        # Fetch active map
        m = universe.get_active_map()

        if (self.direction == DIR_LEFT):

            # Animate irregardless of move's success...
            if ( not (self.move( -(self.speed + 0), 0, universe )) ):

                # Usually we wouldn't have animated, having not moved...
                self.animate()


                # If this entity explodes upon hitting walls...
                if (self.exploding and self.can_move):

                    self.explode(corpse = False, radius = 1, control_center = control_center, universe = universe)

                    # Dipose of the hologram
                    self.expire()

        elif (self.direction == DIR_RIGHT):

            # Animate no matter what
            if ( not (self.move( (self.speed + 0), 0, universe )) ):

                # Usually we wouldn't have animated, having not moved...
                self.animate()


                # If this entity explodes upon hitting walls...
                if (self.exploding and self.can_move):

                    self.explode(corpse = False, radius = 1, control_center = control_center, universe = universe)

                    # Dipose of the hologram
                    self.expire()

        elif (self.direction == DIR_UP):

            if ( not self.move(0, -self.speed, universe) ):

                # Usually we wouldn't have animated, having not moved...
                self.animate()


                # If this entity explodes upon hitting walls...
                if (self.exploding and self.can_move):

                    self.explode(corpse = False, radius = 1, control_center = control_center, universe = universe)

                    # Dipose of the hologram
                    self.expire()

        elif (self.direction == DIR_DOWN):

            if ( not self.move(0, self.speed, universe) ):

                # Usually we wouldn't have animated, having not moved...
                self.animate()


                # If this entity explodes upon hitting walls...
                if (self.exploding and self.can_move):

                    self.explode(corpse = False, radius = 1, control_center = control_center, universe = universe)

                    # Dispose of the hologram
                    self.expire()


    def render(self, sx, sy, sprites, scale, is_editor, gl_color, window_controller = None):

        if ( (self.status == STATUS_ACTIVE) and (self.alive) ):

            if ( (is_editor) or (not self.editor_only) ):

                # Calculate frame
                frame = self.frame_indices[self.direction].get_frame_at_sequence_index(self.frame)

                # Render at 50% opacity (hard-coded)
                window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprites[self.species], scale = scale, gl_color = (0.5, 0.5, 1.0, 0.5 * gl_color[3]), frame = frame)

        # Render particles
        for particle in self.particles:
            particle.render(sx, sy, sprites[self.species], window_controller)


# I also consider the terminal a kind of "NPC"
class Terminal(NPC):

    def __init__(self):

        NPC.__init__(self)

        self.species = "terminal"

        # By default, set class on a terminal to "terminal" (not "npc")
        self.set_class("terminal")

        self.frame_interval = 0
        self.frame_interval_max = TERMINAL_FRAME_DURATION

        # Locked terminals require hacking / pass codes
        self.locked = False
        self.passcode = "12345"


    # Terminals require a special save state function
    def save_state(self):

        # Start with base state
        root = Entity.save_state(self)

        # Add extra properties
        root.set_attributes({
            "locked": xml_encode( "%s" % self.locked ) # I didn't end up using this feature, even!
        })

        # Return node
        return root


    # Terminals require a special load state function,
    # to load the "locked" state that I never even used.  Whatever.
    def load_state(self, node):

        # Load base state
        Entity.load_state(self, node)

        # Check locked status
        self.locked = (node.get_attribute("locked") == "True")


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        self.frame_interval += 1

        if (self.frame_interval >= self.frame_interval_max):

            self.frame_interval = 0

            self.frame += 1

            if (self.frame >= TERMINAL_FRAME_COUNT):
                self.frame = 0

            elif (self.frame == (TERMINAL_FRAME_COUNT - 1)):
                self.frame_interval -= TERMINAL_FINAL_FRAME_PAUSE


        # Process particles
        for particle in self.particles:
            particle.process(None)


    def render(self, sx, sy, sprites, scale, is_editor, gl_color, window_controller = None):

        if (self.status == STATUS_ACTIVE):

            if ( (is_editor) or (not self.editor_only) ):
                window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprites[self.species], scale = scale, gl_color = gl_color, frame = self.frame)

                if (self.locked):
                    window_controller.get_gfx_controller().draw_sprite(sx + self.get_x() + int(self.width / 1) - 6, sy + self.get_y() + int(self.height / 2) - 6, 12, 12, sprites["terminal.lock"], scale = scale, gl_color = gl_color, frame = 0) # I know, this is blatantly hard-coded

        # Render particles
        for particle in self.particles:
            particle.render(sx, sy, sprites[self.species], window_controller)


# I also have an "indicator arrow" NPC object.  It's like an NPC, except it's an arrow.  Get it?
class IndicatorArrow(NPC):

    def __init__(self):

        NPC.__init__(self)


        # NPC species type
        self.species = "indicator-arrow"

        # By default, this will have no class at all
        self.set_class("")


        # The indicator arrow will "pulse" in and out of view.  First, we'll track the delay
        # for which the thing shall wait before fading in/out of view...
        self.delay = 0

        # Next, set up an alpha controller
        self.alpha_controller = IntervalController(
            interval = 0.75,
            target = 0.75,
            speed_in = 0.025,
            speed_out = 0.045
        )


    # Indicator arrow inherits from NPC, which inherits from Enemy.
    # But, indicator arrow has no need for "AI."  we shall overwrite the function here.
    def handle_ai(self, control_center, universe):

        return


    # Indicator arrows support fading
    def fade_in(self):

        # If it's not locked, then let's make sure to lock it
        if ( not self.is_locked() ):

            # We'll unlock this arrow when it finishes its fade in
            self.lock()


        # Always set target on the fade
        self.alpha_controller.configure({
            "target": 0.75
        })

        # Process alpha controller explicitly
        self.alpha_controller.process()

        # Check for fade completion
        if ( self.alpha_controller.get_interval() == self.alpha_controller.get_target() ):

            # Unlock now that we're done
            self.unlock()

            # Return success
            return True

        # Not done yet
        else:

            # Return "not done"
            return False


    # Fade out
    def fade_out(self):

        # If it's not locked, then let's make sure to lock it
        if ( not self.is_locked() ):

            # We'll unlock this arrow when it finishes its fade in
            self.lock()


        # Always set target on the fade
        self.alpha_controller.configure({
            "target": 0.0
        })

        # Process alpha controller explicitly
        self.alpha_controller.process()

        # Check for fade completion
        if ( self.alpha_controller.get_interval() == self.alpha_controller.get_target() ):

            # Unlock now that we're done
            self.unlock()

            # Return success
            return True

        # Not done yet
        else:

            # Return "not done"
            return False


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        # The frame always equals the direction; the arrow has no "animation" to speak of.
        self.frame = self.direction


        # Locked?
        if ( self.is_locked() ):

            pass

        # Do we have a delay?
        elif (self.delay > 0):

            # Wait...
            self.delay -= 1

        else:

            # Process alpha controller
            self.alpha_controller.process()

            # Has the alpha controller finished its fade?
            if ( self.alpha_controller.get_interval() == self.alpha_controller.get_target() ):

                # Did we finish fading in?
                if ( self.alpha_controller.get_target() > 0 ):

                    # Enact a brief delay
                    self.delay = 25

                    # Configure the alpha controller to fade out (after the delay expires)
                    self.alpha_controller.configure({
                        "target": 0.0
                    })

                # No; we just finished fading out.
                else:

                    # Enact a brief delay
                    self.delay = 25

                    # Configure the alpha controller to fade in
                    self.alpha_controller.configure({
                        "target": 0.75
                    })

        return
        self.frame_interval += 1

        if (self.frame_interval >= self.frame_interval_max):

            self.frame_interval = 0

            self.frame += 1

            if (self.frame >= TERMINAL_FRAME_COUNT):
                self.frame = 0

            elif (self.frame == (TERMINAL_FRAME_COUNT - 1)):
                self.frame_interval -= TERMINAL_FINAL_FRAME_PAUSE


        # Process particles
        for particle in self.particles:
            particle.process(None)


    def render(self, sx, sy, sprites, scale, is_editor, gl_color, window_controller = None):

        #print self.name, (self.status == STATUS_ACTIVE)

        if (self.status == STATUS_ACTIVE):

            if ( (is_editor) or (not self.editor_only) ):

                # Get alpha value
                alpha = self.alpha_controller.get_interval()

                # Update given render color
                if ( len(gl_color) > 3 ):

                    # Cross-multiply
                    gl_color = (gl_color[0], gl_color[1], gl_color[2], alpha * gl_color[3])

                else:

                    # Set raw alpha
                    gl_color = (gl_color[0], gl_color[1], gl_color[2], alpha)


                # Render arrow indicator sprite
                window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprites[self.species], scale = scale, gl_color = gl_color, frame = self.frame)

        # Render particles
        for particle in self.particles:
            particle.render(sx, sy, sprites[self.species], window_controller)


class Gold(Entity):

    def __init__(self):

        Entity.__init__(self)

        self.genus = GENUS_GOLD
        self.species = None


        # Allow this piece of gold to move at any time.
        # Gold doesn't move on its own (doesn't obey gravity at all), but planar shifts can move gold pieces.
        self.can_move = True


        # Has the player collected this gold?
        self.collected = False

        # Has an enemy ever carried this gold?  If not, we'll ignore position-related state data (when loading states).
        self.carried = False


        # If an enemy drops a piece of gold they were carrying, they'll signal that this gold should be reactivated...
        self.queued_for_reactivation = False


    # Gold adds more data to ordinary Entity state
    def save_state(self):

        # Start with base data
        root = Entity.save_state(self)

        # Add extra properties
        root.set_attributes({
            "raw-x": xml_encode( "%d" % self.get_x() ),
            "raw-y": xml_encode( "%d" % self.get_y() ),
            "collected": xml_encode( "%s" % self.collected ),
            "carried": xml_encode( "%s" % self.carried )
        })

        # Return node
        return root


    # Gold needs a special load state function
    def load_state(self, node):

        # Load base data
        Entity.load_state(self, node)


        # Force default to active state
        self.set_status(STATUS_ACTIVE)

        # Check collected state
        if ( node.has_attribute("collected") ):
            self.collected = ( node.get_attribute("collected") == "True" )

        # Also check carried state (i.e. has any entity ever carried this gold)
        if ( node.has_attribute("carried") ):
            self.carried = ( node.get_attribute("carried") == "True" )


        # If the player previously collected this gold, then we'll force it to inactive
        if (self.collected):

            # Force inactive
            self.set_status(STATUS_INACTIVE)

        # Perhaps an enemy picked it up and dropped it somewhere else?
        # Let's update the raw position of this gold piece
        elif (self.carried):

            # Obey position-related state data
            self.x = int( node.attributes["raw-x"] )
            self.y = int( node.attributes["raw-y"] )


    def queue_for_reactivation(self):

        self.queued_for_reactivation = True

        log2( "Queueing gold for reactivation:  %s" % self.name )


    def mark_as_collected_by_actor(self, control_center, universe, actor = None):#network_controller, universe, p_map, session, actor = None):

        # It's collected
        self.collected = True

        # Mark as carried, as the player is technically carrying it
        self.carried = True


        # Make sure to deactivate it
        self.set_status(STATUS_INACTIVE)


        # Increase the player's wallet / collection totals
        universe.increment_session_variable("core.gold.found", 1)
        universe.increment_session_variable("core.gold.wallet", 1)


        # Loop through equipped items
        for item in universe.get_equipped_items():

            # Item should handle gold collection; it might have an attribute related to collecting gold...
            item.handle_gold_collection(control_center, universe)


        # Queue a "gold collected" sound effect
        control_center.get_sound_controller().queue_sound(SFX_PLAYER_GRAB_GOLD)


        # Fetch network controller;
        network_controller = control_center.get_network_controller()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # and active map
        m = universe.get_active_map()

        # Create a "gold spinner" on the current map...
        m.create_gold_spinner( self.get_x(), self.get_y() )


        # (?) During netplay, the server will remove the piece of gold from the map, then "sync" that one
        # piece of gold (now collected) to all other players in the game.
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            # Remove this piece of gold from the map's gold cache
            m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )

            # During netplay, the server must sync up all clients when detecting a gold grab
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                network_controller.send_sync_one_gold(self, control_center, universe)


        # (?) During netplay, a client will do nothing more than to remove the gold from the map.
        elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

            # Remove this piece of gold from the map's gold cache
            m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )


        # In single-player mode, we'll have a variety of checks, depending on if we're on a puzzle
        # map, a challenge wave, an overworld map, etc...
        else:

            # If the current wave uses gold rotation, then we'll want to active another piece of gold now...
            size = m.get_wave_tracker().get_wave_param("gold-rotation-size")
            log2( "Map Type:  %s" % m.get_type() )
            log2( "Map Type param:  %s" % size )

            # If we have specified a rotation, then let's activate a new random piece of gold, if/a
            if (size > 0):

                # Find all of the gold entities on this map
                gold_collection = m.get_entities_by_type(GENUS_GOLD)

                log2( "Grabbed gold in challenge room...\nGold collection length:  %d" % len(gold_collection) )

                # Active a random piece of gold in the collection (other than the one we just grabbed)
                m.activate_random_gold_piece_in_collection(gold_collection, exception = self)


                """
                # Track how many pieces of gold we've collected so far...
                m.local_gold_collected += 1

                # Every 5th gold, we add a new enemy...
                if (m.local_gold_collected % 3 == 0):

                    # Advance to the next wave
                    m.next_challenge_wave()
                """


            # On puzzle maps, we remove the gold from the map, then we check for puzzle completion...
            elif ( m.get_type() == "puzzle" ):

                m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )

                # Have we now completed the puzzle?
                if ( m.remaining_gold_count() == 0 ):

                    # Is this the first time we've completed this puzzle room?
                    if (
                        not universe.is_map_completed( universe.get_active_map().name )
                    ):

                        # Mark the map as completed automatically.  Challenge rooms, on the other hand, will require a scripted call because
                        # the conditions for victory can change from wave to wave, etc.
                        universe.mark_map_as_completed( universe.get_active_map().name )

                        # Execute the "puzzle-complete" achievement hook
                        universe.execute_achievement_hook( "puzzle-complete", control_center )


                    # Fetch the menu controller;
                    menu_controller = control_center.get_menu_controller()

                    # and the widget dispatcher
                    widget_dispatcher = control_center.get_widget_dispatcher()


                    # Add a victory menu
                    menu_controller.add(
                        widget_dispatcher.create_puzzle_victory_menu()
                    )


            # On challenge maps, we simply remove the gold from the map.
            # Challenge maps use the wave tracking system to determine victory.
            elif ( m.get_type() == "challenge" ):

                # Remove gold
                m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )


            # on linear levels, we'll autosave the universe (always using autosave slot 1) to track the level's
            # completion, show a newsfeeder message, and execute the on-complete script (if/a).
            elif ( m.get_type() == "linear" ):

                # Remove gold
                m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )

                # Map complete?
                if ( m.remaining_gold_count() == 0 ):

                    # Save linear progress data (mark as complete, best time, etc.)
                    universe.save_linear_progress(control_center, universe)


                    """ Newsfeeder """
                    # Let the player know they've completed the level
                    control_center.get_window_controller().get_newsfeeder().post({
                        "type": NEWS_NET_LEVEL_COMPLETE, # Eh, I'll reuse this for now...
                        "title": localization_controller.get_label("level-complete:label"),
                        "content": localization_controller.get_label("moving-to-next-level:label")
                    })


                    """ On-complete script """
                    # Run global on-map-complete script
                    universe.run_script("global.map.on-complete", control_center)

                    # This script should trigger a transition to a next map, probably on a slight delay (preceiding sleep call)
                    universe.get_active_map().run_script("on-complete", control_center, universe)


            # Otherwise, tell the plane to remove it from its cache...
            else:

                # Remove this piece of gold from the map's gold cache
                m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )


                # Execute the universe's "collect-gold" achievement hook
                universe.execute_achievement_hook( "collect-gold", control_center )

                # Also execute the "wallet-changed" achievement hook here
                universe.execute_achievement_hook( "wallet-changed", control_center )


                # During netplay, the server must sync up all clients when detecting a gold grab
                if ( network_controller.get_status() == NET_STATUS_SERVER ):

                    network_controller.send_sync_one_gold(self, control_center, universe)


                # If that was the last piece of gold during offline play, the player gets an XP bonus...
                elif ( m.remaining_gold_count() == 0 ):

                    #m.letterbox_queue.append( ("footer-right", "40XP bonus!") )


                    # Is this the first time we've completed this map?
                    if (
                        not universe.is_map_completed( universe.get_active_map().name )
                    ):

                        # Mark the map as completed automatically.
                        universe.mark_map_as_completed( universe.get_active_map().name )


                    # Currently hacking in an explicit update for the map data's "gold remaining" counter
                    # to ensure level-complete achievement hook has up-to-date data
                    universe.set_map_gold_remaining( universe.get_active_map().get_name(), 0 )

                    # Execute the "level-complete" achievement hook
                    universe.execute_achievement_hook( "level-complete", control_center )


                    # Validate that we specified an actor...
                    if (actor):

                        # Keep a list of the messages we want to display under the level-up bar.
                        notes = []

                        # Keep a tally of how much xp the player shall earn
                        total_xp = 0


                        # How much XP do you gain for completing a level?
                        xp = int( universe.get_session_variable("core.xp.bonus.completionist").get_value() )

                        # Player always get this bonus
                        if (True):

                            # Add to tally
                            total_xp += xp

                            # Add note
                            notes.append( "Level Complete:  +%d XP (Completionist)" % xp )


                        # How much XP do you gain for completing a level without killing a bad guy?
                        xp = int( universe.get_session_variable("core.xp.bonus.pacifist").get_value() )

                        # How many enemies did the player kill?
                        enemies_killed = universe.get_active_map().get_param("stats.enemies-killed")

                        # Did the player meet that goal?
                        if (enemies_killed == 0):

                            # Add to tally
                            total_xp += xp

                            # Add note
                            notes.append( "0 Enemies Killed:  +%d XP (Pacifist)" % xp )

                        # If not, just add a note about enemies killed
                        else:

                            # Add note
                            notes.append( "%d Enem%s Killed:  +0 XP" % (enemies_killed, "ies" if (enemies_killed > 1) else "y") )


                        # How much XP do you gain for completnig a level without using a bomb?
                        xp = int( universe.get_session_variable("core.xp.bonus.no-bombs").get_value() )

                        # How many bombs did the player use?
                        bombs_used = universe.get_active_map().get_param("stats.bombs-used")

                        # Did the player meet that goal?
                        if (bombs_used == 0):

                            # Add to tally
                            total_xp += xp

                            # Add note
                            notes.append( "0 Bombs Used:  +%d XP (Strategist)" % xp )

                        # If not, just add a note...
                        else:

                            # Add note
                            notes.append( "%d Bomb%s Used:  +0 XP" % (bombs_used, "s" if (bombs_used > 1) else "") )


                        # Increase XP, supplying the notes as a semicolon-separated string (how lame)
                        actor.increase_xp(
                            total_xp,
                            control_center,
                            universe
                        )


                        # Add notes to the HUD
                        control_center.get_window_controller().get_hud().add_notes(notes)


    def mark_as_collected_by_enemy(self, control_center, universe, enemy = None):#network_controller, universe, p_map, session, enemy = None):

        # Mark as carried (but not "collected" by player)
        self.carried = True


        # It's disabled (not officially collected!)
        self.set_status(STATUS_INACTIVE)


        # Fetch network controller
        network_controller = control_center.get_network_controller()

        # Fetch active map
        m = universe.get_active_map()


        # Now, tell the plane to remove it from its cache...
        m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )


        # During netplay, the server must sync up all clients when detecting a gold grab
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            network_controller.send_sync_one_gold(self, control_center, universe)


        # Validate that we specified an enemy...
        if (enemy):

            pass


    # Disable this gold piece
    def disable(self, control_center, universe):

        # Disable it
        self.set_status(STATUS_INACTIVE)

        # In case we queued it for reactivation, disable the flag
        self.queued_for_reactivation = False


        # Fetch network controller
        network_controller = control_center.get_network_controller()

        # Fetch active map
        m = universe.get_active_map()


        # Now, tell the plane to remove it from its cache...
        m.master_plane.remove_gold_from_rect_by_name( self.get_rect(), self.name )


        # During netplay, the server must sync up all clients when detecting a gold grab
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            network_controller.send_sync_one_gold(self, control_center, universe)


    def process(self, control_center, universe):#network_controller, universe, p_map, session):

        if (self.queued_for_reactivation):

            log2( "Reactivating gold:  %s" % self.name )

            # Disable flag
            self.queued_for_reactivation = False

            # Activate gold
            self.set_status(STATUS_ACTIVE)


            # No longer collected
            self.collected = False


            # Fetch active map
            m = universe.get_active_map()

            # Now add it back into the master plane's gold cache
            m.master_plane.add_gold_to_cache(self)


            # Fetch network controller
            network_controller = control_center.get_network_controller()

            # During netplay, the server needs to sync this gold back up to all clients
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                network_controller.send_sync_one_gold(self, control_center, universe)


    def render(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        if ( (self.status == STATUS_ACTIVE) and (not self.collected) ):

            # Render point
            (rx, ry) = (
                sx + int(scale * self.get_x()),
                sy + int(scale * self.get_y())
            )

            # Render gold sprite
            window_controller.get_gfx_controller().draw_sprite(rx, ry, self.width, self.height, sprite, gl_color = gl_color, frame = 0)

            """ Begin DEBUG """
            #window_controller.get_default_text_controller().get_text_renderer().render_with_wrap(self.name, sx + self.get_x() + int(self.width / 2), sy + self.get_y() - 20, (225, 225, 225), align = "center")
            """ End DEBUG """


    def render_scaled(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        if ( (self.status == STATUS_ACTIVE) and (not self.collected) ):

            # Calculate scaled rect
            rRender = self.get_scaled_rect(scale = scale)

            # Get render point
            (rx, ry) = (
                sx + rRender[0],
                sy + rRender[1]
            )

            # Render gold sprite
            window_controller.get_gfx_controller().draw_sprite(rx, ry, self.width, self.height, sprite, scale = scale, gl_color = gl_color, frame = 0)

            """ Begin DEBUG """
            #window_controller.get_default_text_controller().get_text_renderer().render_with_wrap(self.name, sx + self.get_x() + int(self.width / 2), sy + self.get_y() - 20, (225, 225, 225), align = "center")
            """ End DEBUG """


class Lever(Entity):

    def __init__(self):

        Entity.__init__(self)

        self.genus = GENUS_LEVER


        # By default, a ground-mounted lever
        self.mount = DIR_DOWN

        # By default, switched to the left
        self.position = DIR_LEFT


    def configure(self, options):

        # Check lever-specific attributes (mount and position)
        if ( "mount" in options ):
            self.mount = int( options["mount"] )

        if ( "position" in options ):
            self.position = int( options["position"] )


        # For chaining
        return self


    # Overwrite
    def customize(self, options):

        # Call inherited version first
        Entity.customize(self, options)

        # Forward to configure routine
        self.configure(options)


        # For chaining
        return self


    # Levers need a special xml string
    def compile_xml_string(self, prefix = ""):

        xml = "%s<entity " % prefix

        xml += "x = '%d' y = '%d' genus = '%d' ai-behavior = '%d' name = '%s' class = '%s' nick = '%s' title = '%s' mount = '%d' position = '%d' />\n" % ( int(self.get_x() / TILE_WIDTH), int(self.get_y() / TILE_HEIGHT), self.genus, self.ai_state.ai_behavior, self.name.replace("'", "&apos;"), xml_encode(self.class_name), self.nick.replace("'", "&apos;"), self.title.replace("'", "&apos;"), self.mount, self.position)

        return xml


    # Levers require a special save state function
    def save_state(self):

        # Start with basic data
        root = Entity.save_state(self)

        # Add extra properties
        root.set_attributes({
            "raw-x": xml_encode( "%d" % self.get_x() ),
            "raw-y": xml_encode( "%d" % self.get_y() ),
            "position": xml_encode( "%d" % self.position )
        })

        # Return node
        return root


    # Levers require a special load state function
    def load_state(self, node):

        # Load base data
        Entity.load_state(self, node)

        # The lever might have moved (if it's attached to a moving plane)
        self.x = int( node.attributes["raw-x"] )
        self.y = int( node.attributes["raw-y"] )


        # Read in status
        self.status = int( node.attributes["status"] )

        # Read in last known lever position
        self.position = int( node.attributes["position"] )


    # Get lever position
    def get_position(self):

        return self.position


    # Set lever position
    def set_position(self, position):

        self.position = position


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):
        return

    def render(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        frame = 0

        if (self.mount == DIR_DOWN):

            frame = 0

            if (self.position == DIR_RIGHT):
                frame += 1

        if (self.mount == DIR_LEFT):

            frame = 2

            if (self.position == DIR_DOWN):
                frame += 1

        elif (self.mount == DIR_RIGHT):

            frame = 4

            if (self.position == DIR_DOWN):
                frame += 1

        window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, scale = scale, gl_color = gl_color, frame = frame)

        """
        # Debug - Render lever name so that I can easily tell which lever should have which default position
        window_controller.get_default_text_controller().get_text_renderer().render_with_wrap(self.name, sx + self.get_x() + int(self.width / 2), sy + self.get_y() - 20, (225, 225, 225), align = "center")
        """


class Bomb(Entity, ExplodingEntityExt):

    def __init__(self):

        Entity.__init__(self)
        ExplodingEntityExt.__init__(self)

        self.genus = GENUS_BOMB

        # Bombs don't know how to hang on monkey bars
        self.knows_how_to_hang = False


        # How much time remains on the fuse?
        self.fuse_length = BOMB_FUSE_LENGTH


        # Bomb radius
        self.radius = 1

        # Calculate radial effect / gradient radius
        s = (self.radius * TILE_WIDTH)
        self.effect_radius = int( math.sqrt( (s * s) + (s * s) ) )


        # Gradient will flicker as the fuse ebbs
        self.gradient_alpha_factor = 0.0

        # Gradient color (different for remote bombs)
        self.gradient_color1 = (225, 25, 25)
        self.gradient_color2 = (175, 25, 25)

        # Remotely detonated bomb?
        self.remote = False


    def set_radius(self, radius):

        # Update radius
        self.radius = radius

        # Calculate radial gradient radius
        s = (self.radius * TILE_WIDTH)
        self.effect_radius = int( math.sqrt( (s * s) + (s * s) ) )


    def get_radius(self):

        return self.radius


    # Get the current fuse length
    def get_fuse_length(self):

        # Return
        return self.fuse_length


    # Set the fuse length
    def set_fuse_length(self, fuse_length):

        # Set
        self.fuse_length = fuse_length


    def die(self, cause, control_center, universe, with_effects = True, server_approved = None):#, network_controller, universe, p_map, session, with_effects = True, server_approved = None):

        # Use effects?
        if (with_effects):

            # Particle explosion
            for j in range(0, 3):
                for i in range(0, 3):

                    self.particles.append( Particle(self.get_x(), self.get_y(), 0, i, j) )

        # Kill bomb and deactivate it
        self.alive = False
        self.set_status(STATUS_INACTIVE)

        # Bomb never respawns... it's gone.
        self.corpsed = True


    def make_remote(self):

        # Flag as remote
        self.remote = True

        # Set color to yellow
        self.gradient_color1 = (225, 225, 25)
        self.gradient_color2 = (175, 175, 25)


    def is_remote(self):

        return self.remote


    # If you leave the map and leave a remote bomb behind (without detonating it),
    # the map will have to remove it.  Too bad...
    def remove_silently(self):

        self.alive = False
        self.set_status(STATUS_INACTIVE)

        # Remove immediately
        self.corpsed = True


    def process(self, control_center, universe):#, network_controller, universe, p_map, session):

        if ( not self.is_locked() ):

            # Process particles, always...
            for particle in self.particles:
                particle.process(None)


            # If not alive, ignore further processing...
            if (not self.alive):
                return


            # Fetch active map
            m = universe.get_active_map()

            # Do gravity
            self.do_gravity(RATE_OF_GRAVITY, universe)


            # Tick, tock!
            if (self.fuse_length > 0):

                # Define fuse tick points
                tick_interval = 40


                # Bomb makes a tick tock sound at select timer intervals
                tick_points = range(tick_interval, BOMB_FUSE_LENGTH, tick_interval)#(120, 80, 40)

                # I want the tick points in descending order, and I guess I'm too lazy to do a descending range() function...
                tick_points.reverse()

                # Should the bomb tick on the present frame?
                if (self.fuse_length in tick_points):

                    # Bomb tick tick tick sound effect
                    if (not self.is_remote()):
                        self.queue_sound(SFX_BOMB_TICK)


                # Calculate the desired alpha factor for the gradient effect.
                # If we're far from a tick point, then we want no alpha factor at all...
                (gradient_flash_range, gradient_flash_speed) = (
                    int(tick_interval / 3),
                    0.015
                )


                # Do we have any future tick points?
                if (self.fuse_length >= tick_points[-1]):

                    # Value of next tick interval
                    next_tick_interval = max(e for e in tick_points if e <= self.fuse_length)

                    #print next_tick_interval, self.fuse_length

                    # Are we getting close?  If so, increase the alpha factor
                    if ( (self.fuse_length - next_tick_interval) <= gradient_flash_range ):

                        self.gradient_alpha_factor += gradient_flash_speed

                    # Nope; cool off the gradient...
                    else:

                        self.gradient_alpha_factor -= gradient_flash_speed

                        # Don't overshoot
                        if (self.gradient_alpha_factor < 0):
                            self.gradient_alpha_factor = 0

                # No?  Then we're just going to fade away the gradient effect...
                else:

                    self.gradient_alpha_factor -= gradient_flash_speed

                    # Don't overshoot
                    if (self.gradient_alpha_factor < 0):
                        self.gradient_alpha_factor = 0


                self.fuse_length -= 1

                # Time to explode?
                if (self.fuse_length <= 0):

                    # If this is a remotely detonated bomb, I will simply reset the fuse...
                    if (self.remote):

                        self.fuse_length = BOMB_FUSE_LENGTH

                    # Otherwise, the bomb will explode
                    else:

                        self.explode(corpse = True, radius = self.radius, control_center = control_center, universe = universe)


    def render(self, sx, sy, sprite, scale, is_editor, gl_color, window_controller = None):

        # Calculate the current frame
        frame = int( (BOMB_FUSE_LENGTH - self.fuse_length) / BOMB_FUSE_INTERVAL ) % BOMB_FRAME_COUNT

        # Render the bomb
        if (self.alive):

            if (self.fuse_length > 0):

                window_controller.get_geometry_controller().draw_circle_with_radial_gradient(
                    sx + self.get_x() + int(self.width / 2),
                    sy + self.get_y() + int(self.height / 2),
                    self.effect_radius,
                    background1 = set_alpha_for_rgb(self.gradient_alpha_factor * 0.5, self.gradient_color1),
                    background2 = set_alpha_for_rgb(self.gradient_alpha_factor * 0.15, self.gradient_color2)
                )

            window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), self.width, self.height, sprite, scale = scale, gl_color = gl_color, frame = frame)

        # Render particles
        for particle in self.particles:

            particle.render(sx, sy, sprite, window_controller)
