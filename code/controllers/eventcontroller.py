import code.constants.eventtypes as eventtypes

from code.tools.xml import XMLParser

from code.tools.eventqueue import EventQueue

from code.utils.common import log, log2, logn, offset_rect, intersect, log, xml_encode, xml_decode, is_numeric

from code.constants.common import *
from code.constants.states import *

from code.constants.newsfeeder import NEWS_GENERIC_ITEM, NEWS_ITEM_NEW, NEWS_ITEM_LOST, NEWS_ITEM_UPGRADE # The only ones we need (?)


# A simple wrapper
class Event:

    def __init__(self, node, params, origin = ""):

        self.node = node
        self.params = params

        # What triggered this event?  Some trigger name, perhaps?  (Optional)
        self.origin = origin

        # A planar shift, for instance, will not be complete until the plane
        # reaches its destination.
        self.complete = False

        # Some events will have sub-events (conditional, for instance)
        self.event_queue = []

        # Some events (conditionals) will cache the result of their first evaluation for consistent behavior
        self.cached_result = None


# The master controller
class EventController:

    def __init__(self):

        # Keep a queue of scripts wiaitng to run.
        # When we call a script, we'll create a new Script object using a given block of script text data.
        self.scripts = []

        # Some events handle the first frame of an event as a special case (e.g. planar shift doing prep work)
        self.first_frame = True

        # We can enforce arbitrary delays before / after a script executes.
        # Why we would do this, I don't know.  It's uncommon.
        self.delay = 0

    """
    def __init__(self):

        # Keep a queue of events to run
        self.packet_queue = []

        # Event packets will dictate whether we are synchronous or asynchronous
        self.blocking = False

        # Event packets can also request a delay after completion
        self.delay = 0

        # Some events handle the first frame of an event as a special case (e.g. planar shift doing prep work)
        self.first_frame = True

    def load_packets_from_xml_node(self, node, origin = None):

        # Get the packets
        packet_collection = node.get_nodes_by_tag("packet")

        for ref_packet in packet_collection:

            # We'll add each event to a list that represents a single packet of events
            packet = []


            # Get all events
            event_collection = ref_packet.get_nodes_by_tag("event")

            for ref_event in event_collection:

                packet.append( Event(ref_event, {}, origin) )


            # Add the new packet to the queue...
            self.packet_queue.append(packet)

    # This function accepts any XML node (presumably a <packet> but anything will work)
    # and adds the events therein to a new packet...
    def load_events_from_xml_packet(self, node, origin = None):

        # We'll add each event to a list that represents a single packet of events
        packet = []


        # Get all events
        event_collection = node.get_nodes_by_tag("event")

        for ref_event in event_collection:

            packet.append( Event(ref_event, {}, origin) )


        # Add the new packet to the queue...
        self.packet_queue.append(packet)
    """


    # Load a given Script object
    def load(self, script):

        # Debug - looking for old string-based scripts so that I can remove them.
        if ( type(script) == type("") ):
            logn( "script warning", "Script data still uses string data instead of a script object." )
            return


        # Reset the cursor on the given Script object
        script.reset()

        # Create a new Script object with the given data,
        # adding it to our queue of active scripts.
        self.scripts.append(script)


    # Optional means of processing all of the queued events (or as many in one turn as we can)
    def loop(self, control_center, universe):

        result = self.process(control_center, universe)

        while (result == True):

            result = self.process(control_center, universe)


    # Process any active script
    def process(self, control_center, universe):

        # If our queue is empty...
        if ( len(self.scripts) == 0 ):

            # We might still have a delay requested by the final event packet
            if (self.delay > 0):

                self.delay -= 1

            # We have nothing more to do, no script to process.
            return False

        # Otherwise, let's handle the current packet of events...
        else:

            # Are we in a delay from the last script?
            if (self.delay > 0):

                self.delay -= 1

                # We're not done with all of the available script data yet; we're waiting on the delay before continuing.
                return False

            else:

                log( self.scripts )
                # Run / resume the first script in line, retrieving
                # its done/not done status in the process
                complete = self.scripts[0].run(control_center, universe)

                # If we have completed the script, then we can remove it from the queue.
                if (complete):

                    # Remove from queue
                    self.scripts.pop(0)

                    # We're ready to move on to another script at any time.
                    # When we do so, we'll be on the first frame of that script's execution.
                    self.first_frame = True

                    # Return that we completed running this script
                    return True

                # If we haven't completed the script...
                else:

                    # We won't be on the first frame of execution, not next time we resume this script...
                    self.first_frame = False

                    # Return that we haven't yet completed this script
                    return False

    """
    def process(self, control_center, universe):#network_controller, universe, p_map, session, quests):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # If our queue is empty...
        if (len(self.packet_queue) == 0):

            # We might still have a delay requested by the final event packet
            if (self.delay > 0):
                self.delay -= 1

            return False

        # Otherwise, let's handle the current packet of events...
        else:

            # Are we in a delay from the last packet?
            if (self.delay > 0):
                self.delay -= 1

                return False

            else:

                # Default to assuming completion, until we prove otherwise...
                packet_complete = True

                # Get the current event and its post delay
                packet = self.packet_queue[0]


                post_delay = 0

                # Handle the packet's events
                for e in packet:

                    if ( not self.handle_script_command(e, self.first_frame, control_center, universe) ):#network_controller, universe, p_map, session, quests)):
                        packet_complete = False

                # We're not on the first frame any longer...
                self.first_frame = False


                # If every event in this packet has finished, then let's enact
                # any specified delay and remove the packet from the queue...
                if (packet_complete):

                    # Reset any cached result data
                    for e in packet:
                        e.cached_result = None


                    self.delay = post_delay
                    self.packet_queue.pop(0)

                    # Having finished this packet, we'll be in the first frame
                    # of the next packet at some point...
                    self.first_frame = True

                    # When a packet completes, we'll return True so that we know we can immediately hop to the next packet...
                    return True

                else:
                    return False
    """


    # Translate a session variable name into its value...
    def translate_session_variable(self, name, universe):

        # Try to get session variable
        variable = universe.get_session_variable(name)

        # Validate
        if (variable):

            return variable.get_value()

        else:
            return None


    # Evaluate a given expression.
    # Update aliased variables (e.g. session, quest status, etc.) before evaluating.
    def evaluate_expression(self, expression, universe):
        return
        #print 5/0


    """ Obsolete function """
    # Returns True when an event is complete
    def handle_script_command(self, e, first_frame, control_center, universe):#network_controller, universe, p_map, session, quests):

        (node, params) = (e.node, e.params)

        event_key = "%s" % node.get_attribute("type")
        event_type = -1

        if (event_key in eventtypes.TRANSLATIONS):
            event_type = eventtypes.TRANSLATIONS[event_key]

        #print "type = ", event_type

        # Generic dig tile event
        if (event_type == eventtypes.DIG_TILE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                trigger = m.get_trigger_by_name( e.node.get_attribute("target") )

                (tx, ty) = (trigger.x, trigger.y)

                (w, h) = (trigger.width, trigger.height)

                # Will we purge the tile(s)?
                purge = ( int( e.node.get_attribute("purge") ) == 1 )

                # will we force even undiggable tiles to be dug?
                force_dig = ( int( e.node.get_attribute("force") ) == 1)


                # Dig all tiles in the specified target...
                for y in range(ty, ty + h):

                    for x in range(tx, tx + w):

                        m.dig_tile_at_tile_coords(x, y, purge = purge, scripted_dig = True, force_dig = force_dig)


                # Flag event as complete
                e.cached_result = "done"

            # Single-use event
            return True

        # Planar shift event
        elif (event_type == eventtypes.PLANAR_SHIFT):

            # Fetch active map
            m = universe.get_active_map()


            # For security, let's destroy any existing magic wall on the map first...
            m.destroy_magic_wall()


            # Get the plane that will be shifting...
            shifting_plane = m.get_plane_by_name(e.node.get_attribute("plane"))

            # Make sure that (a) no plane is already in mid-shift, or
            #                (b) this plane is the plane in mid-shift
            midshift_plane = m.get_plane_in_midshift()

            if (False and midshift_plane):

                # We're going to have to wait our turn...
                if (midshift_plane != shifting_plane):
                    #return False
                    pass


            # Validate that we found the plane...
            if (shifting_plane):

                # At the beginning of a planar shift, we must for each and every entity
                # calculate which, if any, plane the entity is standing on.  Tiebreaker
                # goes to the highest plane.
                if (e.cached_result != "setup-complete"):

                    # Let's inject a parameter to the event; we'll use it to track which entities the
                    # planar shift's friction will affect.
                    e.params["-affected-entities"] = []

                    log( "Checking for affected entities..." )


                    for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC, GENUS_GOLD, GENUS_BOMB, GENUS_LEVER):

                        for entity in m.master_plane.entities[genus]:

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

                            # Now remove any trace of stowaways until the end of the current planar shift for this plane...
                            shifting_plane.shift_stowaways = []

                            # Will this plane's movement affect the entity?
                            if (affected):

                                # Round to current on-screen position
                                entity.y = entity.get_y()

                                e.params["-affected-entities"].append(entity)

                    log( "affected:  ", e.params["-affected-entities"] )


                    # Set the shifting plane's flag to True
                    shifting_plane.is_shifting = True


                    # Distribute the master plane's trap data to the individual planes...
                    m.distribute_master_trap_data_to_shifting_plane()

                    # We also want to update the master plane... it won't be rendering this particular plane any more...
                    #m.update_master_plane()


                    # Setup is complete
                    e.cached_result = "setup-complete"



                # Let us shift the plane!  Set default targets to the current location...
                x_target = (shifting_plane.x + shifting_plane.shift_x) * TILE_WIDTH
                y_target = (shifting_plane.y + shifting_plane.shift_y) * TILE_HEIGHT

                t = m.get_trigger_by_name( e.node.get_attribute("target") )

                if (t):
                    x_target = (t.x * TILE_WIDTH)
                    y_target = (t.y * TILE_HEIGHT)

                # Check parameters
                if ("x" in e.node.attributes):
                    x_target = int( float(e.node.get_attribute("x")) * TILE_WIDTH )

                if ("y" in e.node.attributes):
                    y_target = int( float(e.node.get_attribute("y")) * TILE_HEIGHT ) 


                speed = float( e.node.get_attribute("speed") )

                if (speed == 0):
                    speed = 1.0


                # By default, a plane can shift through other tiles.  If the attribute is specified as colliding, though, then it collides...
                ghost = (int( e.node.get_attribute("collides") ) == 0)


                result = shifting_plane.shift_to_target(x_target, y_target, speed, ghost, e.params["-affected-entities"], m)

                # If the shift has completed, then let's toggle the flag and update the master plane...
                if (result == True):

                    shifting_plane.dx = 0
                    shifting_plane.dy = 0

                    # Remember which entities are still affected by this plane's shifting...
                    shifting_plane.shift_stowaways = e.params["-affected-entities"]

                    # Occasionally I set plane shifts to end at uneven intervals.  When this happens, I don't update the master plane.
                    # The script MUST return the plane to an even interval, or the plane will not rejoin the master plane.
                    if ( (shifting_plane.shift_x % TILE_WIDTH == 0) and (shifting_plane.shift_y % TILE_HEIGHT == 0) ):

                        # Return trap data tracking from the individual planes to the master plane...
                        m.recollect_master_trap_data_from_shifting_plane()

                    shifting_plane.is_shifting = False

                    if ( (shifting_plane.shift_x % TILE_WIDTH == 0) and (shifting_plane.shift_y % TILE_HEIGHT == 0) ):

                        # Update the master plane
                        #m.update_master_plane()

                        m.master_plane.build_gold_cache()


                    # No more stowaways; this ride is over!
                    shifting_plane.shift_stowaways = []


                    for z in e.params["-affected-entities"]:
                        log( z.name, " = ", z.y )


                return result

            # Couldn't find the plane...
            else:
                return False

        # Planar slide
        elif (event_type == eventtypes.PLANAR_SLIDE):

            # Fetch active map
            m = universe.get_active_map()


            # For security, let's destroy any existing magic wall on the map first...
            m.destroy_magic_wall()


            # Which plane will slide?
            sliding_plane = m.get_plane_by_name(e.node.get_attribute("plane"))

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



            if (sliding_plane):

                # Sliding up is easy...
                if (slide == DIR_UP or slide == -1):

                    # On the first frame, we should flag the plane as sliding and such
                    if (e.cached_result != "done"):

                        sliding_plane.is_sliding = True

                        sliding_plane.active = True

                        e.cached_result = "done"


                    # Slide the plane...
                    result = sliding_plane.planar_slide(slide, speed, target_name, m)

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


                    return result

                # Sliding down will end up squishing entities in the way...
                elif (slide == DIR_DOWN):

                    # First frame flag fun
                    if (e.cached_result != "done"):

                        sliding_plane.is_sliding = True

                        # Assume that we want the plane to slide down from 0 slide
                        sliding_plane.slide_y = 0
                        #print 5/0

                        # Plane is now active
                        sliding_plane.active = True


                        e.cached_result = "done"


                    # Just slide...
                    result = sliding_plane.planar_slide(slide, speed, target_name, m)

                    # Done?
                    if (result):

                        sliding_plane.is_sliding = False

                        # Just to be sure
                        sliding_plane.active = True


                        # Update master plane; map state has changed.
                        #m.update_master_plane()


                    return result

            else:
                return True

        # Planar message
        elif (event_type == eventtypes.PLANAR_MESSAGE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                plane = m.get_plane_by_name( e.node.get_attribute("plane") )

                if (plane):

                    if ( plane.handle_message( e.node.get_attribute("message"), e.node.get_attribute("param"), control_center, universe ) ):

                        # Flag message as processed
                        e.cached_result = "done"

                    else:
                        pass

                else:
                    # Flag message as processed
                    e.cached_result = "done"

            # Single-use event
            return (e.cached_result == "done")

        elif (event_type == eventtypes.CUTSCENE_BEGIN):

            # Fetch active map
            m = universe.get_active_map()


            # For security, let's destroy any existing magic wall on the map first...
            m.destroy_magic_wall()

            # Set status to cutscene
            m.status = STATUS_CUTSCENE

            return True

        elif (event_type == eventtypes.CUTSCENE_END):

            # Fetch active map
            m = universe.get_active_map()

            # Return to active map status
            m.status = STATUS_ACTIVE

            return True

        elif (event_type == eventtypes.DEBUG):
            log2( "Debug message:  %s" % e.node.get_attribute("msg") )
            return True


        # If statement
        elif (event_type == eventtypes.CONDITION_IF):

            # Default behavior
            behavior = "comparison"

            # Assume failure by default
            result = False


            # Check for explicit behavior
            if ( e.node.has_attribute("behavior") ):

                # Update
                behavior = e.node.get_attribute("behavior")


            # Do we want to evaluate a given expression?
            if (behavior == "expression"):

                # Try to get cached result first
                result = e.cached_result

                # No prior result?
                if (result == None):

                    # Evaluate expression
                    result = self.evaluate_expression(
                        "%s" % e.node.get_attribute("expression")
                    )

            # Do we want to quickly compare two values?
            elif (behavior == "comparison"):

                #print "If... (", first_frame, ")"

                (variable1, operator, variable2, raw_value) = (
                    self.translate_session_variable(e.node.get_attribute("variable1"), universe),
                    e.node.get_attribute("operator"),
                    self.translate_session_variable(e.node.get_attribute("variable2"), universe),
                    e.node.get_attribute("raw-value")
                )

                # raw value always wins
                if (raw_value != ""):
                    variable2 = raw_value


                # Try to get cached result first
                result = e.cached_result

                # Didn't find one?
                if (result == None):

                    if (operator == "=="):

                        phrase = "'%s' == '%s'" % (variable1, variable2)
                        #print phrase, "???"

                        result = eval(phrase)

                    elif (operator == ">"):

                        phrase = "%s > %s" % (variable1, variable2)
                        result = eval(phrase)

                    elif (operator == ">="):

                        phrase = "%s >= %s" % (variable1, variable2)
                        result = eval(phrase)

                    elif (operator == "<"):

                        phrase = "%s < %s" % (variable1, variable2)
                        result = eval(phrase)

                    elif (operator == "<="):

                        phrase = "%s <= %s" % (variable1, variable2)
                        result = eval(phrase)

                    elif (operator == "!="):

                        phrase = "%s != %s" % (variable1, variable2)
                        result = eval(phrase)

                    else:
                        result = False


                # Cache the result for next time
                e.cached_result = result

                # When true, get all of the "then" nodes...
                if (result):

                    ref_then = e.node.get_nodes_by_tag("event", {"type": "condition-then"})

                    if (len(ref_then) > 0):

                        # Get all consequential events
                        event_collection = ref_then[0].get_nodes_by_tag("event")

                        # For now, especially since we don't know if we have any events, we assume we're finished...
                        event_complete = True


                        # Immediately handle any of the consequential events
                        for ref_event in event_collection:

                            e2 = Event(ref_event, {})
                            e.event_queue.append(e2)

                            # All events must return True to maintain "event complete" status
                            #if (not self.handle_script_command(e2, first_frame, p_map, session)):
                            #    event_complete = False


                        #return event_complete


                # Otherwise, let's check for "else" consequences...
                else:

                    ref_else = e.node.get_nodes_by_tag("event", {"type": "condition-else"})

                    if (len(ref_else) > 0):

                        # Get all alternative events
                        event_collection = ref_else[0].get_nodes_by_tag("event")

                        # For now, especially since we don't know if we have any events, we assume we're finished...
                        event_complete = True


                        # Immediately handle any of the alternative events
                        for ref_event in event_collection:

                            e2 = Event(ref_event, {})
                            e.event_queue.append(e2)

                            # All events must return True to maintain "event complete" status
                            #if (not self.handle_script_command(e2, first_frame, p_map, session)):
                            #    event_complete = False


                        #return event_complete


            event_complete = True

            for each in e.event_queue:

                #print "prcessing '%s'" % each.node.get_attribute("type")

                if ( not self.handle_script_command(each, first_frame, control_center, universe) ):#network_controller, universe, p_map, session, quests)):
                    event_complete = False

            return event_complete


        # Switch statement (with "when" children)
        elif (event_type == eventtypes.CONDITION_SWITCH):

            if (e.cached_result != "computed"):

                log( "computing when..." )


                # Default switch type is session variable
                switch_type = "variable"

                # Check for explicit type
                if ( e.node.has_attribute("switch-type") ):

                    # Update switch type
                    switch_type = e.node.get_attribute("switch-type")


                # Scope
                variable1 = None


                # Session variable switch?
                if (switch_type == "variable"):

                    # What value will we use for the switch?
                    variable1 = self.translate_session_variable( e.node.get_attribute("variable"), universe )

                # Quest status switch?
                elif (switch_type == "quest-status"):

                    # Find the quest to check
                    quest = universe.get_quest_by_name( e.node.get_attribute("quest") )

                    # Validate
                    if (quest):

                        # Update variable 1 to given status
                        variable1 = quest.get_status()


                # Query for all WHEN children...
                when_collection = e.node.get_nodes_by_tag("event", {"type": "condition-when"})

                for ref_when in when_collection:

                    # What's the value of this when?  Raw value always wins...
                    variable2 = self.translate_session_variable( ref_when.get_attribute("variable"), universe )
                    raw_value = ref_when.get_attribute("raw-value")

                    if (raw_value != ""):
                        variable2 = raw_value


                    # Use this when?
                    phrase = "'%s' == '%s'" % (variable1, variable2)
                    log( "phrase = '%s'" % phrase )
                    result = eval(phrase)

                    if (result):

                        # Get all consequential WHEN events...
                        event_collection = ref_when.get_nodes_by_tag("event")

                        # Save all of these as the switch's descendants...
                        for ref_event in event_collection:

                            e2 = Event(ref_event, {})
                            e.event_queue.append(e2)

                # We've computed this switch now...
                e.cached_result = "computed"


            # Check all child events...
            event_complete = True

            for each in e.event_queue:
                if ( not self.handle_script_command(each, first_frame, control_center, universe) ):#network_controller, universe, p_map, session, quests)):
                    event_complete = False

            return event_complete

        # Dialogue (with possible responses)
        elif (event_type in (eventtypes.DIALOGUE, eventtypes.DIALOGUE_FYI, eventtypes.DIALOGUE_SHOP, eventtypes.DIALOGUE_COMPUTER)):

            # Fetch active map
            m = universe.get_active_map()


            # Check the cached result . If we set it, that means we processed
            # this dialogue; we are simply waiting for the map to let us know
            # the dialogue has ended.
            if (e.cached_result == None):

                # Don't commit to a new dialogue iteration until any existing dialogue concludes
                if ( m.is_dialogue_finished() ):

                    entity = m.get_entity_by_name( e.node.get_attribute("entity") )
                    conversation = e.node.get_attribute("conversation")

                    if (entity):

                        # When beginning a conversation, we always start at the root.
                        # So, yes, right now this is just hard-coded (branches["root"]).
                        line = entity.conversations[conversation].branches["root"].get_next_line()

                        # Validate
                        if (line):

                            # Fetch the widget dispatcher;
                            widget_dispatcher = control_center.get_widget_dispatcher()

                            # and the menu controller;
                            menu_controller = control_center.get_menu_controller()

                            # and the splash controller
                            splash_controller = control_center.get_splash_controller()


                            #m.create_dialogue_panel(line, universe, session, quests, conversation, entity, event_type = event_type)# = (event_type == eventtypes.DIALOGUE_SHOP))

                            # Does the line have any pre-script data that we should try to process?
                            if (line.pre_script):

                                # I want to handle these events immediately.  You can't use blocking events (successfully) in a pre-script...
                                controller = EventController()

                                controller.load_packets_from_xml_node(line.pre_script)


                                # Run for as long as possible.  You can only inject simple single-use events...
                                result = controller.process(control_center, universe)#universe, self, session, quests)

                                while (result == True):

                                    result = controller.process(control_center, universe)#universe, self, session, quests)


                            # Create a shopping dialogue panel?
                            if (event_type == eventtypes.DIALOGUE_SHOP):

                                # Pause game action
                                universe.pause()

                                # Call for a pause splash
                                splash_controller.set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)

                                # Add a "shopping" dialogue panel (configured to look identical with a real shop menu for visual consistency
                                # when we switch to a real shop menu).
                                menu_controller.add(
                                    widget_dispatcher.create_shopping_dialogue_panel().configure({
                                        "narrator": entity,
                                        "conversation-id": conversation,
                                        "redirect": line.redirect,
                                        "source-node": line
                                    })
                                )

                            # Create a computer dialogue panel?
                            elif (event_type == eventtypes.DIALOGUE_COMPUTER):

                                # Here we must make a choice.  If none of the responses has "details" (e.g. e-mail etc.), then
                                # we're going to fall back to a simple RowMenu-ish version of the dialogue.
                                if ( 1 or all( o.details == "" for o in line.responses ) ):

                                    self.dialogue_panel = DialoguePanelComputerSimple(line, universe, session, conversation, entity, event_type)

                                # Otherwise, we'll show a full-fledged "computer" dialogue panel
                                else:

                                    self.dialogue_panel = DialoguePanelComputer(line, universe, session, conversation, entity, event_type)


                            # FYI dialogue panel (narrate cutscenes, etc., does not respond at all to user input)
                            elif (event_type == eventtypes.DIALOGUE_FYI):

                                # Add an "FYI" dialogue panel.
                                # Note that FYI dialogue panels come with an explicit id, unlike other dialogue panel types.
                                menu_controller.add(
                                    widget_dispatcher.create_fyi_dialogue_panel().configure({
                                        "id": e.node.get_attribute("id"),
                                        "narrator": entity,
                                        "conversation-id": conversation,
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
                                        "narrator": entity,
                                        "conversation-id": conversation,
                                        "redirect": line.redirect,
                                        "source-node": line
                                    })
                                )

                    # Just flag cache_result as True (any value would do!) to indicate
                    # that we've activated the dialogue and any response...
                    e.cached_result = True

                else:

                    return False


            # Now check the map to determine the result of this packet event 
            return m.is_dialogue_finished()


        # Dismiss the FYI dialogue panel.  This simply raises a "continue" event, as if the player had hit enter on an ordinary dialogue.
        elif (event_type == eventtypes.DISMISS_FYI):

            if (e.cached_result != "done"):

                # What is the id of the FYI we want to dismiss?
                menu_id = e.node.get_attribute("id")

                # Get a reference to that fyi dialogue panel
                panel = control_center.get_menu_controller().get_menu_by_id(menu_id)

                # Validate
                if (panel):

                    # Raise a "continue" event
                    panel.fire_event("continue")


                # Flag event as done
                e.cached_result = "done"


            # Single-use event
            return True


        # Toggle dialogue line enabled / disabled status
        elif (event_type == eventtypes.DIALOGUE_UPDATE_LINES_AND_RESPONSES):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                entity_name = e.node.get_attribute("entity")

                # Get the referring entity
                entity = m.get_entity_by_name(entity_name)

                log( entity_name, entity )

                # Validate
                if (entity):

                    # Which conversation?
                    conversation = entity.get_conversation_by_id( e.node.get_attribute("conversation") )

                    log( conversation )

                    # Validate further
                    if (conversation):

                        # Update all conversation branches per specification
                        conversation.update_lines_and_responses_by_selector(
                            selector = e.node.get_attribute("selector"),
                            active = ( int(e.node.get_attribute("active")) == 1 )
                        )


                #entity.set_conversation_line_status(conversation_id, line_id, active)

                e.cached_result = "done"

            # Single-use event
            return True


        # Dialogue response
        elif (event_type == eventtypes.DIALOGUE_RESPONSE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Add the answer/response to the current map dialogue
                m.add_dialogue_response(e.node.get_attribute("answer"), e.node.get_attribute("message"))

                e.cached_result = "done"

            # Single-use event
            return True


        # Shop with an NPC (view their actual warehouse-based inventory)
        elif (event_type == eventtypes.SHOP):

            # Fetch the widget dispatcher;
            widget_dispatcher = control_center.get_widget_dispatcher()

            # and the menu controller;
            menu_controller = control_center.get_menu_controller()

            # and the splash controller
            splash_controller = control_center.get_splash_controller()


            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Who's selling?  (NPC name)
                entity_name = e.node.get_attribute("entity")

                # Get a handle to that entity
                entity = m.get_entity_by_name(entity_name)


                # Validate
                if (entity):

                    # Decide which options we need for the Shop Menu.  Start with the XML attributes...
                    options = e.node.get_attributes()

                    # Inject NPC vendor into options hash
                    options["vendor"] = entity


                    # Add a Shopping Menu
                    menu_controller.add(
                        widget_dispatcher.create_shop_menu().configure(
                            options
                        )
                    )


                    log2( "Now we're shopping... game should remain paused" )

                else:
                    log( "Unable to validate entity..." )


                e.cached_result = "done"

            else:

                return False


            # Only mark this event as completed when the shop menu has faded away (user has bought something or cancelled the menu)
            return True#(not m.is_busy())


        # Show the puzzle intro widget (begin puzzle, leave puzzle, whatever)
        elif (event_type == eventtypes.PUZZLE_INTRO):

            # Fetch the widget dispatcher;
            widget_dispatcher = control_center.get_widget_dispatcher()

            # and the menu controller;
            menu_controller = control_center.get_menu_controller()

            # and the splash controller
            splash_controller = control_center.get_splash_controller()


            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Summon pause splash
                splash_controller.set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


                # Default options to any given node attributes
                options = e.node.get_attributes()

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


                e.cached_result = "done"


            # Single-use event
            return True


        # Entity message
        elif (event_type == eventtypes.ENTITY_MESSAGE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                entity = m.get_entity_by_name( e.node.get_attribute("entity") )
                #print entity

                if (entity):

                    #print entity, e.node.get_attribute("message"), e.node.get_attribute("param")
                    #if ( e.node.get_attribute("message") == "set-speed" ):
                    #    print 5/0

                    if ( entity.handle_message( e.node.get_attribute("message"), e.node.get_attribute("target"), e.node.get_attribute("param"), control_center, universe ) ):

                        # Flag message as processed
                        e.cached_result = "done"

                    else:
                        pass

                else:
                    # Flag message as processed
                    e.cached_result = "done"

                    #print e.node.compile_xml_string()
                    #print 5/0

            # Single-use event
            return (e.cached_result == "done")

        # Call script
        elif (event_type == eventtypes.CALL_SCRIPT):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                script = "%s" % e.node.get_attribute("script")

                log2( "Let's call '%s'..." % script )

                if ( m.does_script_exist(script) ):
                    m.event_controller.load_packets_from_xml_node(m.scripts[script])

                else:
                    log2( "Doesn't exist!" )

                e.cached_result = "done"

            # Single-use event
            return True


        # Set a map param
        elif (event_type == eventtypes.SET_MAP_PARAM):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Which param are we setting?
                name = e.node.get_attribute("name")

                # What value are we assigning?
                value = xml_decode( e.node.get_attribute("value") )


                # Set param
                m.set_param(name, value)


                # Flag as done
                e.cached_result = "done"

                log( m.params )


            # Single-use event
            return True


        # Set a wave param
        elif (event_type == eventtypes.SET_WAVE_PARAM):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Which wave param will we set?
                name = e.node.get_attribute("name")

                # What will we set it to?
                value = xml_decode( e.node.get_attribute("value") )

                # This is hacky, but I'm going to cast the string value into an integer if it's numeric.
                # In theory, only the on-complete param and the timer id / label params will ever use a non-numeric value.
                if ( is_numeric(value) ):

                    value = int(value)


                # Set the wave param
                m.get_wave_tracker().set_wave_param(name, value)


                # Flag as done
                e.cached_result = "done"


            # Single-use event
            return True


        # Set a wave allowance (e.g. start with 5 bombs).  Must be a numeric string, or it will do nothing.
        elif (event_type == eventtypes.SET_WAVE_ALLOWANCE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Which wave allowance will we set?
                name = e.node.get_attribute("name")

                # What will we set it to?
                value = xml_decode( e.node.get_attribute("value") )

                # Allowances must always be numeric values
                if ( is_numeric(value) ):

                    value = int(value)

                    # Set the wave allowance
                    m.get_wave_tracker().set_wave_allowance(name, value)

                else:
                    log2( "Warning:  Cannot set wave allowance '%s' to non-numeric value '%s!'" % (name, value) )


                # Flag as done (we tried, anyway)
                e.cached_result = "done"


            # Single-use event
            return True


        # Set a wave requirement (e.g. collect 10 bars of gold).  Must be a numeric string, or this event does nothing.
        elif (event_type == eventtypes.SET_WAVE_REQUIREMENT):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Which wave allowance will we set?
                name = e.node.get_attribute("name")

                # What will we set it to?
                value = xml_decode( e.node.get_attribute("value") )

                # Requirements must always be numeric values
                if ( is_numeric(value) ):

                    value = int(value)

                    # Set the wave requirement
                    m.get_wave_tracker().set_wave_requirement(name, value)

                else:
                    log2( "Warning:  Cannot set wave requirement '%s' to non-numeric value '%s!'" % (name, value) )


                # Flag as done (we tried, anyway)
                e.cached_result = "done"


            # Single-use event
            return True


        # Set a wave limit (i.e. kill no more than 5 enemies).  Must be a numeric string, otherwise this event does nothing.
        elif (event_type == eventtypes.SET_WAVE_LIMIT):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Which limit are we setting?
                name = e.node.get_attribute("name")

                # What shall we set it to?
                value = xml_decode( e.node.get_attribute("value") )

                # Limits must be numeric
                if ( is_numeric(value) ):

                    value = int(value)

                    # Set the limit
                    m.get_wave_tracker().set_wave_limit(name, value)

                else:
                    log2( "Warning:  Cannot set wave limit '%s' to non-numeric value '%s!'" % (name, value) )


                # Mark as done (or tried)
                e.cached_result = "done"


            # Single-use event
            return True


        # Reset to a new wave in the current map (e.g. progress to next wave)
        elif (event_type == eventtypes.NEW_WAVE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # Simply reset the wave tracker
                m.reset_wave_tracker()


                # Mark as done
                e.cached_result = "done"


            # Single-use event
            return True


        # (?) Show a "wave intro" menu
        elif (event_type == eventtypes.WAVE_INTRO):

            if (e.cached_result != "done"):

                # Fetch active map
                m = universe.get_active_map()


                # Default options to any given node attributes
                options = e.node.get_attributes()

                # Fetch other attributes, such as text fills, from the map's params...
                options["overview"] = "%s" % m.get_param("overview")


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


                # Mark as done
                e.cached_result = "done"


            # Single-use event
            return True


        # Show a "wave progress chart" letting the user know what they need to do (or not do), and what allowances they have remaining.
        elif (event_type == eventtypes.SHOW_WAVE_PROGRESS_CHART):

            # Ported to new scripting engine
            """
            if (e.cached_result != "done"):

                # Fetch active map
                m = universe.get_active_map()

                # Get the wave tracker
                wave_tracker = m.get_wave_tracker()


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


                # Mark as done
                e.cached_result = "done"
            """


            # Single-use event
            return True


        # Rebuild the "wave progress chart."  Typically called after a new save begins.  Does nothing if the wave progress chart does not exist.
        elif (event_type == eventtypes.REBUILD_WAVE_PROGRESS_CHART):

            if (e.cached_result != "done"):

                # Fetch active map
                m = universe.get_active_map()

                # Grab the wave tracker
                wave_tracker = m.get_wave_tracker()


                # Get the wave progress chart menu
                wave_progress_chart = control_center.get_menu_controller().get_menu_by_id("wave-progress-chart")

                # Validate
                if (wave_progress_chart):

                    # Reconfigure theh chart with fresh wave tracker data
                    wave_progress_chart.configure({
                        "tracked-requirement-names": wave_tracker.get_active_wave_requirement_names(),
                        "tracked-limit-names": wave_tracker.get_active_wave_limit_names(),
                        "tracked-allowance-names": wave_tracker.get_active_wave_allowance_names()
                    })

                    # Fire a new build event
                    wave_progress_chart.fire_event("build")


                # Flag as done (or attempted)
                e.cached_result = "done"


            # Single-use event
            return True


        # Create a timer on the universe by a given name with a single param (the event to fire on complete).
        # Length must be a numeric string, or this event will do nothing.
        elif (event_type == eventtypes.CREATE_TIMER):

            if (e.cached_result != "done"):

                # Name of the timer
                name = e.node.get_attribute("name")

                # Length of the timer
                length = e.node.get_attribute("length")

                # Measure of the length (frames, seconds, etc.)
                measure = e.node.get_attribute("measure")

                # The event to fire when the timer completes
                on_complete = e.node.get_attribute("on-complete")


                # The length must be numeric.
                if ( is_numeric(length) ):

                    # Cast the raw length as a float, first...
                    length = float(length)

                    # Measure in frames, we will simply go with an integer...
                    if (measure == "frames"):

                        length = int(length)

                    # Seconds?
                    elif (measure == "seconds"):

                        length = int(60 * length) # 60 FPS (hard-coded)

                    # Default to frames, if no measure (or an invalid measure) is given.
                    else:

                        length = int(length)


                # Create singular timer object (for now, just a single use).
                universe.get_timer_controller().add_singular_event_with_name(name, length, on_complete = on_complete, params = {})


                # Flag as done
                e.cached_result = "done"


            # Single-use event
            return True


        # Clear an existing timer by name.  Does nothing if the timer does not exist.
        elif (event_type == eventtypes.CLEAR_TIMER):

            if (e.cached_result != "done"):

                # Timer name
                name = e.node.get_attribute("name")

                # Try to remove the timer.  Fails gracefully, silently.
                universe.get_timer_controller().remove_timer_by_name(name)


                # Flag as done (or attempted)
                e.cached_result = "done"


            # Single-use event
            return True


        # Increment an existing timer by some value.  Does nothing if the timer does not exist.  Value must be numeric.
        elif (event_type == eventtypes.INCREMENT_TIMER):

            if (e.cached_result != "done"):

                # Timer name
                name = e.node.get_attribute("name")

                # Increment value
                value = e.node.get_attribute("value")

                # Measure type (seconds, frames, leave blank to default to frames)
                measure = e.node.get_attribute("measure")


                # Try to get timer
                timer = universe.get_timer_controller().get_timer_by_name(name)

                # Validate
                if (timer):

                    # Value must be numeric
                    if ( is_numeric(value) ):

                        # Check measure
                        if (measure == "frames"):

                            # Cast into integer
                            value = int(value)

                        elif (measure == "seconds"):

                            # Cast into integer * seconds
                            value = int(60 * value) # 60 FPS (hard-coded)

                        # Default to frames
                        else:

                            # Cast into integer
                            value = int(value)


                        # Increment timer by given interval
                        timer.increment(value)


                    else:
                        log2( "Warning:  Cannot increment timer '%s' by non-numeric value '%s!'" % (name, value) )


        # Trigger message
        elif (event_type == eventtypes.TRIGGER_MESSAGE):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                trigger = m.get_trigger_by_name( e.node.get_attribute("target") )
                entity_name = e.node.get_attribute("entity")

                message = e.node.get_attribute("message")
                param = "%s" % e.node.get_attribute("param")

                m.send_message_to_trigger(trigger, entity_name, message, param, universe)#, p_map, session)
                #trigger.handle_message(entity_name, message, param, universe, p_map)

                # Flag message as processed
                e.cached_result = "done"

            # Single-use event
            return True


        # Trigger contains calculation
        elif (event_type == eventtypes.TRIGGER_CONTAINS):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                entity = m.get_entity_by_name( e.node.get_attribute("entity") )
                trigger = m.get_trigger_by_name( e.node.get_attribute("target") )

                variable = e.node.get_attribute("variable")

                #print (entity, trigger, variable)

                if (intersect(trigger.get_rect(is_editor = False), entity.get_rect())): # is_editor always False if we're running live events...
                    universe.set_session_variable(variable, "1")
                    #print 5/0

                else:
                    universe.set_session_variable(variable, "0")

                # Flag calculation as completed
                e.cached_result = "done"

            # Single-use event
            return True

        # Lever has position calculation
        elif (event_type == eventtypes.LEVER_HAS_POSITION):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                entity = m.get_entity_by_name( e.node.get_attribute("entity") )
                position = int( e.node.get_attribute("position") )

                variable = e.node.get_attribute("variable")

                if (entity.genus == GENUS_LEVER):

                    if (entity.position == position):
                        universe.set_session_variable(variable, "1")

                    else:
                        universe.set_session_variable(variable, "0")

                else:
                    universe.set_session_variable(variable, "0")

                # Flag calculation as completed
                e.cached_result = "done"

            # Single-use event
            return True

        # Cutscene control
        elif (event_type == eventtypes.CUTSCENE_CONTROL):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                behavior = e.node.get_attribute("behavior")

                if (behavior == "begin"):
                    m.status = STATUS_CUTSCENE

                elif (behavior == "end"):
                    m.status = STATUS_ACTIVE

                # Flag cutscene control as complete
                e.cache_result = "done"

            # Single-use event
            return True

        # Increase a session variable
        elif (event_type == eventtypes.VARS_PLUS):

            if (e.cached_result != "done"):

                # It should be a numerical value, but we'll wrap it in a try/except just in case...
                try:

                    """
                    previous_value = int( universe.get_[e.node.get_attribute("variable")]["value"] )
                    amount = int( e.node.get_attribute("amount") )
                    new_value = previous_value + amount

                    session[e.node.get_attribute("variable")]["value"] = "%d" % new_value
                    """

                    universe.increment_session_variable( e.node.get_attribute("variable"), int( e.node.get_attribute("amount") ) )
                    log( "**Increment succeeded!!!" )

                except:
                    pass

                # Flag calculation as completed
                e.cached_result = "done"

            # Single-use event
            return True

        # Set a session variable
        elif (event_type == eventtypes.VARS_SET):

            if (e.cached_result != "done"):

                universe.set_session_variable( e.node.get_attribute("variable"), "%s" % e.node.get_attribute("value") )

                log( "session[", e.node.get_attribute("variable"), "] = ", universe.get_session_variable( e.node.get_attribute("variable") ).get_value() )

                # Flag calculation as completed
                e.cached_result = "done"

            # Single-use event
            return True

        # Sum two numeric session variables into a 3rd session variable
        elif (event_type == eventtypes.VARS_SUM):

            if (e.cached_result != "done"):

                try:

                    (a, b) = (
                        int( universe.get_session_variable_using_session( e.node.get_attribute("variable1"), session ).get_value() ),
                        int( universe.get_session_variable_using_session( e.node.get_attribute("variable2"), session ).get_value() )
                    )

                    # Update target session variable
                    universe.set_session_variable_using_session( e.node.get_attribute("variable3"), "%d" % (a + b), session )

                except:

                    # Fall back to 0 on error
                    universe.set_session_variable_using_session( e.node.get_attribute("variable3"), "0", session )

                # Flag calculation as completed
                e.cached_result = "done"

            # Single-use event
            return True

        # Copy one session variable's value to another's...
        elif (event_type == eventtypes.VARS_COPY):

            if (e.cached_result != "done"):

                #session[e.node.get_attribute("variable2")]["value"] = session[e.node.get_attribute("variable1")]["value"]
                universe.set_session_variable( e.node.get_attribute("variable2"), universe.get_session_variable( e.node.get_attribute("variable1") ).get_value() )

                # Flag calculation as completed
                e.cached_result = "done"

            # Single-use event
            return True


        # Set an NPC indicator
        elif (event_type == eventtypes.SET_NPC_INDICATOR):

            if (e.cached_result != "done"):

                # Look for the target NPC
                entity = universe.get_active_map().get_entity_by_name( e.node.get_attribute("entity") )

                # Validate
                if (entity):

                    # Set indicator value
                    entity.set_indicator(
                        e.node.get_attribute("key"),
                        e.node.get_attribute("value")
                    )


                # Mark event as processed
                e.cached_result = "done"

            # Single-use event
            return True


        # Enable lines in a given conversation with a given class for a given NPC
        elif (event_type == eventtypes.DIALOGUE_ENABLE_LINES_BY_CLASS):

            if (e.cached_result != "done"):

                # Look for the target NPC
                entity = universe.get_active_map().get_entity_by_name( e.node.get_attribute("entity") )

                # Validate
                if (entity):

                    # Attempt to enable given lines
                    entity.enable_conversation_lines_by_class(
                        e.node.get_attribute("conversation"),
                        e.node.get_attribute("class")
                    )


                # Done processsing
                e.cached_result = "done"

            # Single-use event
            return True


        # Disable lines in a given conversation with a given class for a given NPC
        elif (event_type == eventtypes.DIALOGUE_DISABLE_LINES_BY_CLASS):

            if (e.cached_result != "done"):

                # Look for the target NPC
                entity = universe.get_active_map().get_entity_by_name( e.node.get_attribute("entity") )

                # Validate
                if (entity):

                    # Attempt to enable given lines
                    entity.disable_conversation_lines_by_class(
                        e.node.get_attribute("conversation"),
                        e.node.get_attribute("class")
                    )


                # Done processsing
                e.cached_result = "done"

            # Single-use event
            return True


        # Flag quest event
        elif (event_type == eventtypes.FLAG_QUEST):

            if (e.cached_result != "done"):

                log( "FLAG QUEST EVENT!" )

                for quest in universe.get_quests():

                    if (quest.get_name() == e.node.get_attribute("quest")):

                        quest.flag( e.node.get_attribute("flag"), control_center, universe )

                e.cached_result = "done"

            # Single-use event
            return True

        # Flag quest update event
        elif (event_type == eventtypes.FLAG_QUEST_UPDATE):

            if (e.cached_result != "done"):

                for quest in universe.get_quests():

                    if ( quest.get_name() == e.node.get_attribute("quest") ):

                        # Get the given update name
                        update_name = e.node.get_attribute("update")

                        # Get given flag
                        flag = e.node.get_attribute("flag")


                        # Flag the given update for this quest
                        quest.flag_update_by_name(update_name, flag, control_center, universe)


                # Mark as completed
                e.cached_result = "done"

            # Single-use event
            return True


        # Fetch quest status
        elif (event_type == eventtypes.FETCH_QUEST_STATUS):

            if (e.cached_result != "done"):

                for quest in universe.get_quests():

                    if ( quest.get_name() == e.node.get_attribute("quest") ):

                        # Update the specified session variable...
                        universe.set_session_variable( e.node.get_attribute("variable"), "%s" % quest.get_status_phrase( format = e.node.get_attribute("format") ) )

                e.cached_result = "done"

            # Single-use event
            return True

        # Fetch quest update status
        elif (event_type == eventtypes.FETCH_UPDATE_STATUS):

            if (e.cached_result != "done"):

                for quest in universe.get_all_quests():

                    if ( quest.name == e.node.get_attribute("quest") ):

                        for update in quest.updates:

                            if (update.name == e.node.get_attribute("update")):

                                # Update the specified session variable...
                                #session[e.node.get_attribute("variable")]["value"] = "%s" % update.get_status_phrase(format = e.node.get_attribute("format"))
                                universe.set_session_variable( e.node.get_attribute("variable"), "%s" % update.get_status_phrase( format = e.node.get_attribute("format") ) )

                e.cached_result = "done"

            # Single-use event
            return True

        # OBSOLETE:  Trigger map overlay
        elif (event_type == eventtypes.OVERLAY):

            if (e.cached_result != "done"):

                log( "Obsolete event:  Create Overlay" )
                e.cached_result = "done"

            # Single-use event
            return True

        # Camera message
        elif (event_type == eventtypes.CAMERA_MESSAGE):

            if (e.cached_result != "done"):

                # zap?
                if (e.node.get_attribute("message") == "zap"):

                    pass

                # pan on entity
                elif (e.node.get_attribute("message") == "pan"):

                    pass

                e.cached_result = "done"

            # Single-use event
            return True

        # Reload map
        elif (event_type == eventtypes.RELOAD_MAP):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                # We already heard your request, hold on...
                if (not m.requires_reload):

                    # Flag the map to reload itself at the end of all processing
                    m.requires_reload = True

                    m.reload_delay = int( e.node.get_attribute("delay") )

                e.cached_result = "done"

            # Single-use event
            return True

        # Mark map as completed
        elif (event_type == eventtypes.MARK_MAP_AS_COMPLETED):

            if (e.cached_result != "done"):

                # Mark the current map as completed...
                universe.mark_map_as_completed( universe.get_active_map().name )

                e.cached_result = "done"

            # Single-use event
            return True

        # Set the active map's status message (e.g Collect #a / #b gold)
        elif (event_type == eventtypes.SET_MAP_STATUS_MESSAGE):

            if (e.cached_result != "done"):

                # Mark the current map as completed...
                universe.get_active_map().set_status_message(
                    universe.translate_session_variable_references( xml_decode( e.node.get_attribute("message") ) )
                )

                e.cached_result = "done"

            # Single-use event
            return True

        # Sleep event
        elif (event_type == eventtypes.SLEEP):

            # Start at 0
            if (e.cached_result == None):

                e.cached_result = 0

                return False

            # Sleep for [param] frames
            elif (e.cached_result < int( e.node.get_attribute("frames") )):

                e.cached_result += 1

                return False

            else:

                return True

        # Spawn random enemy
        elif (event_type == eventtypes.SPAWN_RANDOM_ENEMY):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                is_disposable = (e.node.get_attribute("disposable") == "yes")

                name = ""

                if (e.node.get_attribute("param")):
                    name = e.node.get_attribute("param")

                enemy = m.create_random_enemy(is_disposable = is_disposable, name = name)

                enemy.respawn_region_name = e.node.get_attribute("target")

                e.cached_result = "done"

            # Single-use event
            return True

        # Remove (i.e. kill, then corpse) any random enemy on the map
        elif (event_type == eventtypes.REMOVE_RANDOM_ENEMIES):

            if (e.cached_result != "done"):

                # Grab active map
                m = universe.get_active_map()

                # Remove the random enemies
                m.remove_random_enemies(control_center, universe)


                # Flag as done
                e.cached_result = "done"


            # Single-use event
            return True

        # Load new map
        elif (event_type == eventtypes.LOAD_MAP):

            if (e.cached_result != "done"):

                # Get the window controller
                window_controller = control_center.get_window_controller()

                # Before we begin a fade, the window controller is going to need to remember what
                # map we're going to, which waypoint we were at, and which waypoint we're going to.
                window_controller.set_param( "to:map", e.node.get_attribute("name") )
                window_controller.set_param( "to:waypoint", e.node.get_attribute("spawn") )
                window_controller.set_param( "from:waypoint", e.origin )                        # The trigger that spawned this event

                # Hook into the window controller os that it can forward us an event after it fades
                window_controller.hook(self)

                # App fade
                window_controller.fade_out(
                    on_complete = "fwd:finish:load-map"
                )


                # As we are fading out, we want to set the universe to paused.  We'll unpause the game
                # when we receive word that the fade has concluded.
                universe.pause()

                # I guess we'll use the greyscale effect, though we won't really see much of it as the window fades out...
                control_center.get_splash_controller().set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)

                """
                # Transition to the new map...
                universe.transition_to_map(
                    name = e.node.get_attribute("name"),
                    waypoint_to = e.node.get_attribute("spawn"),
                    waypoint_from = e.origin, # Which trigger (name) triggered this call?
                    control_center = control_center
                )
                """

                e.cached_result = "done"

            # This event will never end.  When the new map is loaded, this map object will simply disappear... this is the end of the road for this map and its event controller...
            return False

        # Letterbox shout
        elif (event_type == eventtypes.SHOUT):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                m.letterbox_queue.append((
                    e.node.get_attribute("position"),
                    e.node.get_attribute("message")
                ))

                e.cached_result = "done"

            # Single-use event
            return True


        # Post a generic newsfeeder item
        elif (event_type == eventtypes.POST_NEWSFEEDER_ITEM):

            if (e.cached_result != "done"):

                # Post a generic newsfeeder item
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": xml_decode( e.node.get_attribute("title") ),
                    "content": xml_decode( e.node.get_attribute("content") )
                })

                # Flag as done
                e.cached_result = "done"


            # Single-use event
            return True


        # Fetch stat (into session variable)
        elif (event_type == eventtypes.FETCH_STAT):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                statistic = e.node.get_attribute("statistic")
                variable_key = e.node.get_attribute("variable")

                entity = m.get_entity_by_name( e.node.get_attribute("entity") )

                if (statistic == "enemies-left"):

                    #session[variable_key]["value"] = "%d" % m.count_living_enemies()
                    universe.set_session_variable( variable_key, "%d" % m.count_living_enemies() )

                elif (statistic == "gold-left"):

                    #session[variable_key]["value"] = "%d" % m.remaining_gold_count()
                    universe.set_session_variable( variable_key, "%d" % m.remaining_gold_count() )
                    log( "gold left:  ", m.remaining_gold_count() )
                    log( "", variable_key, " = ", universe.get_session_variable(variable_key).get_value() )

                elif (statistic == "is-locked"):

                    #session[variable_key]["value"] = "%d" % entity.locked
                    universe.set_session_variable( variable_key, "%d" % entity.locked )

                else:

                    pass

                e.cached_result = "done"

            # Single-use event
            return True

        # Fetch stat by region (into session variable)
        elif (event_type == eventtypes.FETCH_STAT_BY_REGION):

            # Fetch active map
            m = universe.get_active_map()

            if (e.cached_result != "done"):

                statistic = e.node.get_attribute("statistic")
                variable_key = e.node.get_attribute("variable")

                entity = m.get_entity_by_name( e.node.get_attribute("entity") )
                t = m.get_trigger_by_name( e.node.get_attribute("target") )

                #print statistic, variable_key, t
                #print 5/0

                if (statistic == "enemies-left"):

                    #session[variable_key]["value"] = "%d" % m.count_living_enemies()
                    log( "needs region?!" )
                    log( 5/0 )
                    universe.set_session_variable( variable_key, "%d" % m.count_living_enemies() )

                elif (statistic == "gold-left"):

                    #session[variable_key]["value"] = "%d" % m.remaining_gold_count( t.get_rect() )
                    universe.set_session_variable( variable_key, "%d" % m.remaining_gold_count( t.get_rect() ) )

                elif (statistic == "gold-collected"):

                    #session[variable_key]["value"] = "%d" % m.collected_gold_count( t.get_rect() )
                    universe.set_session_variable( variable_key, "%d" % m.collected_gold_count( t.get_rect() ) )

                elif (statistic == "gold-total"):

                    #session[variable_key]["value"] = "%d" % m.get_gold_count( t.get_rect() )
                    universe.set_session_variable( variable_key, "%d" % m.get_gold_count( t.get_rect() ) )

                elif (statistic == "is-locked"):

                    #session[variable_key]["value"] = "%d" % entity.locked
                    universe.set_session_variable( variable_key, "%d" % entity.locked )

                else:

                    pass

                e.cached_result = "done"

            # Single-use event
            return True


        # Acquire an item
        elif (event_type == eventtypes.ACQUIRE_ITEM):

            if (e.cached_result != "done"):

                # Get the name of the item
                name = e.node.get_attribute("name")

                # Acquire the item
                if ( universe.acquire_item_by_name(name) ):

                    # Post a newsfeeder item
                    control_center.get_window_controller().get_newsfeeder().post({
                        "type": NEWS_ITEM_NEW,
                        "title": control_center.get_localization_controller().get_label("new-item-acquired:header"),
                        "content": universe.get_item_by_name(name).get_title()
                    })


                # Flag as done
                e.cached_result = "done"


            # Single-use event
            return True


        # Lose an item


        # (?) Upgrade an item


        # Fetch inventory item stat (into session variable)
        elif (event_type == eventtypes.FETCH_ITEM_STAT):

            if (e.cached_result != "done"):

                statistic = e.node.get_attribute("statistic")
                variable_key = e.node.get_attribute("variable")

                item_name = e.node.get_attribute("item")

                if (statistic == "is-acquired"):

                    #session[variable_key]["value"] = "%d" % universe.is_item_acquired(item_name)
                    universe.set_session_variable( variable_key, "%d" % universe.is_item_acquired(item_name) )

                    log( "session[%s] value = %d (item '%s')" % (variable_key, universe.is_item_acquired(item_name), item_name) )

                elif (statistic == "is-equipped"):

                    #session[variable_key]["value"] = "%d" % universe.is_item_equipped(item_name)
                    universe.set_session_variable( variable_key, "%d" % universe.is_item_equipped(item_name) )

                else:

                    pass

                e.cached_result = "done"

            # Single-use event
            return True

        # Set inventory itme stat
        elif (event_type == eventtypes.SET_ITEM_STAT):

            if (e.cached_result != "done"):

                statistic = e.node.get_attribute("statistic")
                value = e.node.get_attribute("value")

                item_name = e.node.get_attribute("item")

                universe.modify_item_statistic(item_name, statistic, value)

                e.cached_result = "done"

            # Singlue use event
            return True

        # Unknown event type; return complete
        else:
            log( "Unknown event" )
            return True


    # Handle an event
    def handle_event(self, event, control_center, universe):

        # Events that result from event handling
        results = EventQueue()

        # Convenience
        action = event.get_action()


        if (action == "fwd:finish:load-map"):

            results.append(
                self.handle_fwd_finish_load_map_event(event, control_center, universe)
            )


    # (Fwd) Finish up load map logic, post-fade.  Transition the universe to the new map, then fade app back in.
    def handle_fwd_finish_load_map_event(self, event, control_center, universe):

        # Events that results from handling the event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Unhook
        window_controller.unhook(self)


        # We paused the game for the duration of the window fade; now let's unpause the game as
        # we prepare to transition to the new map.
        universe.unpause()

        # We can abort the splash controller now, as well
        control_center.get_splash_controller().abort()


        # Transition to the new map
        universe.transition_to_map(
            name = window_controller.get_param("to:map"),
            waypoint_to = window_controller.get_param("to:waypoint"),
            waypoint_from = window_controller.get_param("from:waypoint"),
            control_center = control_center
        )

        """
                universe.transition_to_map(
                    name = e.node.get_attribute("name"),
                    waypoint_to = e.node.get_attribute("spawn"),
                    waypoint_from = e.origin, # Which trigger (name) triggered this call?
                    control_center = control_center
                )
        """


        # App fade back in, as we arrive on the new map
        window_controller.fade_in()
