import random

#from gridmenu import GridMenuCell
#from rowmenu import RowMenu

#from glfunctions import draw_rect, draw_rect_frame, draw_triangle, draw_rounded_rect, draw_rounded_rect_with_gradient

from code.tools.eventqueue import EventQueue

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import evaluate_spatial_expression, intersect, offset_rect, log, xml_encode, xml_decode, set_alpha_for_rgb

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_WIDTH, TILE_HEIGHT, TRIGGER_BEHAVIOR_WAYPOINT, TRIGGER_BEHAVIOR_PASSIVE, TRIGGER_BEHAVIOR_ACTIVATED, TRIGGER_BEHAVIOR_NONE, TRIGGER_BEHAVIOR_INTERVAL, TRIGGER_BEHAVIOR_FOLLOWING, TRIGGER_BEHAVIOR_ALARM, ALARM_LASER_SIZE, GENUS_PLAYER, INPUT_ACTION, DIR_DOWN

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.network import NET_STATUS_OFFLINE, NET_STATUS_SERVER, NET_STATUS_CLIENT


class Trigger:

    #def __init__(self, name, x, y, w, h, behavior, prompt):
    #def __init__(self, widget_dispatcher = None, xml = None, universe = None, session = None):
    def __init__(self):

        self.name = ""

        # A trigger may optionally have a class (or classes)
        self.class_name = ""

        self.x = 0
        self.y = 0

        self.width = 1
        self.height = 1


        # A trigger may display a "prompt" (e.g. Press enter to talk to NPC) when the player touches it...
        self.prompt = ""
        self.prompt_tooltip = None

        # Will the prompt include an icon?
        self.show_icon = True


        # The advertisement will appear instead of the prompt when the
        # player is not touching the trigger (e.g. "Challenge room 1 - Completed")
        self.advertisement = ""
        self.advertisement_tooltip = None

        # How does this trigger behave?
        self.behavior = 1

        # Which script(s), if any, wiill this trigger execute?
        self.scripts = {
            "touch": [],
            "hover": [],
            "exit": []
        }


        # By default, a trigger begins as active...
        self.active = True

        # Is a trigger hovered upon?  (I use this to control singular firing of onEnter and onExit events)
        self.hovered = False


        # Used for interval triggers (player never directly interacts with these...)
        self.interval = 0
        self.interval_delay = 15

        # Used for knowing which entity to follow (if it's a follower trigger)
        self.leading_entity = None


        # Should we show the prompt?
        self.show_prompt = False


        #if (xml):
        #    self.load(widget_dispatcher, xml, universe, session)


    def configure(self, options):#widget_dispatcher, xml, universe, session):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "class" in options ):
            self.class_name = options["class"]

        if ( "prompt" in options ):
            self.prompt_text = options["prompt"]

        if ( "x" in options ):
            self.x = int( options["x"] )

        if ( "y" in options ):
            self.y = int( options["y"] )

        if ( "width" in options ):
            self.width = int( options["width"] )

        if ( "height" in options ):
            self.height = int( options["height"] )

        if ( "behavior" in options ):
            self.behavior = int( options["behavior"] )

        if ( "show-icon" in options ):
            self.show_icon = ( int( options["show-icon"] ) == 1 )

        if ( "prevent-caching" in options ):
            self.prevent_caching = ( int( options["prevent-caching"] ) == 1 )

        """
        self.name = xml.get_attribute("name")

        self.x = int( xml.get_attribute("x") )
        self.y = int( xml.get_attribute("y") )

        self.width = int( xml.get_attribute("width") )
        self.height = int( xml.get_attribute("height") )

        self.prompt_text = xml_decode( xml.get_attribute("prompt") )
        self.behavior = int( xml.get_attribute("behavior") )
        """


        # For chaining
        return self


    # Get trigger's name
    def get_name(self):

        # Return
        return self.name


    # Check to see if this Trigger has a given class
    def has_class(self, class_name):

        # Check all classes given to this Trigger
        return any( o == class_name for o in self.class_name.split(" ") )


    def setup_events_from_node(self, node):

        # Check each type of script event (touch, hover, exit)
        for key in self.scripts:

            # Find the connected event collection, if/a
            ref = node.get_first_node_by_tag(key)

            # Validate
            if (ref):

                # Get all connected events of the current type
                script_collection = ref.get_nodes_by_tag("script")

                # Add each
                for ref_script in script_collection:

                    self.add_script_by_type( ref_script.get_attribute("name"), key )


        # For chaining
        return self


    def get_rect(self, is_editor = False):

        # In editor mode, always return the raw region
        if (is_editor):

            return (self.x * TILE_WIDTH, self.y * TILE_HEIGHT, self.width * TILE_WIDTH, self.height * TILE_HEIGHT)


        else:

            # In game mode, alarm triggers will offset the rect to the size of the laser...
            if (self.behavior == TRIGGER_BEHAVIOR_ALARM):

                # Is it a y-axis laser or an x-axis laser?  The dimensions of the trigger will determine...
                if (self.height >= self.width):

                    r = (self.x * TILE_WIDTH, self.y * TILE_HEIGHT, ALARM_LASER_SIZE, self.height * TILE_HEIGHT)

                    r = offset_rect(r, x = int(TILE_WIDTH / 2) - int(ALARM_LASER_SIZE / 2))

                    return r

                # The tiebreaker went to a y-axis laser
                else:

                    r = (self.x * TILE_WIDTH, self.y * TILE_HEIGHT, self.width * TILE_WIDTH, ALARM_LASER_SIZE)

                    r = offset_rect(r, x = int(TILE_HEIGHT / 2) - int(ALARM_LASER_SIZE / 2))

                    return r

            # Otherwise, all other triggers behave normally...
            else:

                # Does this trigger follow an entity?
                if (self.leading_entity):

                    #print "leading:  ", self.leading_entity.get_y(), " (", self.leading_entity.y, ")"

                    (cx, cy) = (
                        self.leading_entity.get_x() + int(self.leading_entity.width / 2),
                        self.leading_entity.get_y() + int(self.leading_entity.height / 2)
                    )

                    (x, y) = (
                        cx - int( (self.width * TILE_WIDTH) / 2),
                        cy - int( (self.height * TILE_HEIGHT) / 2)
                    )

                    return (x, y, self.width * TILE_WIDTH, self.height * TILE_HEIGHT)

                else:
                    return (self.x * TILE_WIDTH, self.y * TILE_HEIGHT, self.width * TILE_WIDTH, self.height * TILE_HEIGHT)


    # Get a scaled rect (for editor purposes)
    def get_scaled_rect(self, scale = 1.0):

        return (
            self.x * int(scale * TILE_WIDTH),
            self.y * int(scale * TILE_HEIGHT),
            int(scale * self.width * TILE_WIDTH),
            int(scale * self.height * TILE_HEIGHT)
        )


    def populate_dropdown_with_scripts_by_type(self, elem, key):

        elem.clear()

        for s in self.scripts[key]:
            elem.add(s, s)


    def add_script_by_type(self, s, key):

        # Prevent duplicates
        if (not (s in self.scripts[key])):
            self.scripts[key].append(s)


    def remove_script_by_type(self, s, key):

        i = 0
        while (i < len(self.scripts[key])):

            if (self.scripts[key][i] == s):
                self.scripts[key].pop(i)

            else:
                i += 1


    def compile_xml_string(self, prefix = ""):

        # Create root node
        root = XMLNode("trigger")

        # Set properties
        root.set_attributes({
            "name": xml_encode(self.name),
            "x": xml_encode( "%d" % self.x ),
            "y": xml_encode( "%d" % self.y ),
            "width": xml_encode( "%d" % self.width ),
            "height": xml_encode( "%d" % self.height ),
            "behavior": xml_encode( "%d" % self.behavior ),
            "prompt": xml_encode(self.prompt_text)
        })

        # If this trigger has a class name, then save that as well
        if (self.class_name != ""):

            # Set extra attribute
            root.set_attributes({
                "class": self.class_name
            })


        # Loop script categories
        for category in self.scripts:

            # Create a node for this category (e.g. touch, hover, etc.)
            node = root.add_node(
                XMLNode(category)
            )

            # Loop scripts assigned to this category
            for s in self.scripts[category]:

                # Add node
                node.add_node(
                    XMLNode("script").set_attributes({
                        "name": xml_encode(s)
                    })
                )

        # Return the raw xml...
        return root.compile_xml_string()

        """
        #xml = "%s<trigger name = '%s' x = '%d' y = '%d' width = '%d' height = '%d' behavior = '%d' prompt = '%s'>\n" % (prefix, self.name, self.x, self.y, self.width, self.height, self.behavior, xml_encode(self.prompt_text))

        for key in self.scripts:

            xml += "%s\t<%s>\n" % (prefix, key)

            for s in self.scripts[key]:
                xml += "%s\t\t<script name = '%s' />\n" % (prefix, s)

            xml += "%s\t</%s>\n" % (prefix, key)

        xml += "%s</trigger>\n" % prefix

        return xml
        """


    # Some inheriting classes will overwrite this with additional data
    def save_state(self):

        # Create node
        node = XMLNode("trigger")

        # Set trigger attributes
        node.set_attributes({
            "name": xml_encode(self.name),
            "active": xml_encode( "%s" % self.active )
        })

        #xml = "%s<trigger name = '%s' active = '%s' />\n" % (prefix, self.name, self.active)

        # Return node
        return node


    # Same deal here; some will overwrite the recall function...
    def load_state(self, node):

        # Check for active attribute
        if ( node.has_attribute("active") ):

            # Read setting
            self.active = ( node.get_attribute("active") == "True" )


    def set_prompt_visibility(self, visibility, control_center, universe):

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Set visibility
        self.show_prompt = visibility

        if (self.show_prompt):

            # If we haven't constructed the prompt tooltip yet (and we don't until we need to),
            # this is the time!
            if (not self.prompt_tooltip):

                # Fetch the widget dispatcher
                widget_dispatcher = control_center.get_widget_dispatcher()

                # Create the tooltip
                self.prompt_tooltip = widget_dispatcher.create_trigger_tooltip().configure({
                    "width": 210, # hard-coded
                    "show-icon": self.show_icon,
                    "prevent-caching": False,
                    "class": "asdf"
                })


                # Special case for "talk" tooltips (e.g. Press ENTER to talk to NPC NAME)
                if ( self.prompt_text.startswith("@talk") ):

                    # Apply secondary translations
                    self.prompt_tooltip.configure({
                        "text": localization_controller.get_label(
                            "press-n-to-talk-to-m:label",
                            {
                                "@n": "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ),
                                "@m": self.prompt_text.replace("@talk:", "")
                            }
                        )
                    })

                # Another special case for "do" tooltips (e.g. Press ENTER to ACTIVATE LEVER)
                elif ( self.prompt_text.startswith("@do") ):

                    # Apply secondary translations
                    self.prompt_tooltip.configure({
                        "text": localization_controller.get_label(
                            "press-n-to-do-m:label",
                            {
                                "@n": "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ),
                                "@m": self.prompt_text.replace("@do:", "")
                            }
                        )
                    })

                # Default to given text
                else:

                    self.prompt_tooltip.configure({
                        "text": self.prompt_text
                    })


    # Get current prompt
    def get_prompt(self):

        # Return
        return self.prompt_text


    # Follow a given entity, by entity object
    def follow_entity(self, entity):

        # Track
        self.leading_entity = entity


    # Enable this trigger
    def enable(self):

        # Active
        self.active = True


    # Disable this trigger
    def disable(self):

        # Not active
        self.active = False


    # Check active status
    def is_active(self):

        # Check
        return self.active


    # Get absolute x position
    def get_x(self):

        # Return
        return (self.x * TILE_WIDTH)


    # Get absolute y position
    def get_y(self):

        # Return
        return (self.y * TILE_HEIGHT)


    # Get tiled x position
    def get_tx(self):

        # Return
        return self.x


    # Get tiled y position
    def get_ty(self):

        # Return
        return self.y


    def handle_message(self, unused, entity_name, message, param, universe):#, p_map, session):

        if (message == "follow"):

            self.leading_entity = universe.get_active_map().get_entity_by_name(entity_name)

        elif (message == "activate"):

            self.active = True

        elif (message == "deactivate"):

            self.active = False

        elif (message == "advertisement"):

            # Store the advertisement text
            self.advertisement = param

            # Build the advertisement tooltip
            self.advertisement_tooltip = None


            # Empty advertisement?
            if (self.advertisement == ""):

                # Cancel that tooltip...
                self.advertisement_tooltip = None


    # Returns True for an activated trigger that the player is touching.
    # Returns False otherwise.
    def process(self, control_center, universe, is_editor = False, masked = False):#widget_dispatcher, network_controller, universe, p_map, session, user_input, is_editor):

        # Inactive triggers do nothing...
        if (not self.active):

            return False


        if ( (self.advertisement_tooltip == None) and (self.advertisement != "") ):

            # Fetch the widget dispatcher
            widget_dispatcher = control_center.get_widget_dispatcher()

            self.advertisement_tooltip = widget_dispatcher.create_trigger_tooltip().configure({
                "text": self.advertisement,
                "width": 210, # hard-coded
                "show-icon": False,
                "prevent-caching": False
            })



        if (self.prompt_tooltip):

            self.prompt_tooltip.process(control_center, universe)

        if (self.advertisement_tooltip):

            self.advertisement_tooltip.process(control_center, universe)


        # Does this trigger follow an entity?
        if (self.leading_entity):

            #print "leading:  ", self.leading_entity.get_y(), " (", self.leading_entity.y, ")"

            (cx, cy) = (
                self.leading_entity.get_x() + int(self.leading_entity.width / 2),
                self.leading_entity.get_y() + int(self.leading_entity.height / 2)
            )

            (x, y) = (
                cx - int( (self.width * TILE_WIDTH) / 2),
                cy - int( (self.height * TILE_HEIGHT) / 2)
            )

            self.x = int(x / TILE_WIDTH)
            self.y = int(y / TILE_HEIGHT)


        #print "%s.rect == %s, behavior == %s, hovered = %s" % (self.get_rect(False), self.name, self.behavior, self.hovered)


        # Is this a tangible trigger that the player can actively (or passively) interact with?
        if (self.behavior in (TRIGGER_BEHAVIOR_PASSIVE, TRIGGER_BEHAVIOR_ACTIVATED, TRIGGER_BEHAVIOR_ALARM)):

            r = self.get_rect(is_editor)

            # Assume
            self.set_prompt_visibility(False, control_center, universe)


            # Fetch active map
            m = universe.get_active_map()

            # Check for any player intersection...
            #for entity in m.master_plane.entities[GENUS_PLAYER]:
            entity = universe.get_local_player()

            if (entity):

                # Get collision rectangle
                rEntity = entity.get_rect()

                # Check intersection... and make sure the player is actually alive and able to interact
                if ( ( intersect(r, rEntity) ) and ( entity.get_status() == STATUS_ACTIVE ) ):

                    # Fetch the network controller;
                    network_controller = control_center.get_network_controller()

                    # and the input controller
                    input_controller = control_center.get_input_controller()


                    # Fetch the gameplay input to use as user input
                    user_input = input_controller.get_gameplay_input()


                    # A passive / alarm trigger will manage hover state and fire scripts as necessary...
                    if (self.behavior in (TRIGGER_BEHAVIOR_PASSIVE, TRIGGER_BEHAVIOR_ALARM)):

                        # First time in the trigger region?
                        if (not self.hovered):

                            self.hovered = True

                            # Fire onEnter events...
                            for s in self.scripts["touch"]:
                                #m.event_controller.load_packets_from_xml_node( m.scripts[s] )
                                m.run_script(s, control_center, universe)
                                log( "fire script:  %s" % s )


                        # Fire any onHover event
                        for s in self.scripts["hover"]:
                            #m.event_controller.load_packets_from_xml_node( m.scripts[s] )
                            m.run_script(s, control_center, universe)


                    # An activated trigger will display a prompt (e.g. "Press [action] to flip the switch") and await such input...
                    elif (self.behavior == TRIGGER_BEHAVIOR_ACTIVATED):

                        # First time in the trigger region?
                        if (not self.hovered):

                            self.hovered = True

                            # Fire onEnter events...
                            for s in self.scripts["touch"]:
                                #m.event_controller.load_packets_from_xml_node( m.scripts[s] )
                                m.run_script(s, control_center, universe)


                        # If this trigger is not "masked" (by another trigger, most likely), then let's show the prompt
                        if (not masked):

                            # Make it visible
                            self.set_prompt_visibility(True, control_center, universe)

                            # Check for activation key
                            if (INPUT_ACTION in user_input):

                                # We store on activation events in the onHover collection
                                for s in self.scripts["hover"]:

                                    # Offline mode - run script immediately
                                    if ( network_controller.get_status() == NET_STATUS_OFFLINE):

                                        #m.event_controller.load_packets_from_xml_node( m.scripts[s], origin = self.name )
                                        m.run_script(s, control_center, universe)

                                    # The server runs the script, then sends a command to all other players to do the same
                                    elif ( network_controller.get_status() == NET_STATUS_SERVER):

                                        # Don't respond to input if a local / global lock is in place on the network controller
                                        if ( not network_controller.is_local_locked() ):

                                            # Run script
                                            #m.event_controller.load_packets_from_xml_node( m.scripts[s], origin = self.name )
                                            #log2( "Needs origin?!!!" )
                                            m.run_script(s, control_center, universe)

                                            # Command clients
                                            network_controller.send_call_script(s, control_center, universe)

                                    # A client cannot directly run a script.  The client can only
                                    # send a request to run that script to the server.
                                    elif ( network_controller.get_status() == NET_STATUS_CLIENT):

                                        # Don't respond to input if a local / global lock is in place on the network controller
                                        if ( not network_controller.is_local_locked() ):

                                            # The server will have to approve it and provide an explicit "run script" command
                                            network_controller.send_script_request(s, control_center, universe)


                            # Return True to indicate that this activated trigger wlll check for player input.
                            # No overlapping trigger should have access to player input during overlap.
                            return True


                # Passive / alarm triggers will check for potential onexit events
                else:

                    if (self.behavior in (TRIGGER_BEHAVIOR_PASSIVE, TRIGGER_BEHAVIOR_ACTIVATED, TRIGGER_BEHAVIOR_ALARM)):

                        # Were we previously on the trigger?
                        if (self.hovered):

                            self.hovered = False

                            # Fire onExit events
                            for s in self.scripts["exit"]:
                                #m.event_controller.load_packets_from_xml_node( m.scripts[s] )
                                m.run_script(s, control_center, universe)

        elif (self.behavior == TRIGGER_BEHAVIOR_INTERVAL):

            self.interval -= 1

            #print self.interval

            if (self.interval <= 0):

                # Fetch the active map
                m = universe.get_active_map()


                # Reset the interval delay
                self.interval = self.interval_delay

                #print "%s:  " % self.name, self.scripts
                #print self.scripts["hover"]
                # We use the onhover script for interval timers.  That's just how it is!
                for s in self.scripts["hover"]:

                    #m.event_controller.load_packets_from_xml_node( m.scripts[s] )
                    m.run_script(s, control_center, universe)


        # Default
        return False


    def draw(self, sx, sy, additional_sprites, text_renderer, show_name = True, show_frame = False, is_editor = False, is_cutscene = False, window_controller = None, scale = 1.0):

        # Debug
        #return

        #show_frame = True
        #show_name = True

        # Skip rendering during "cutscenes" (or, in the currently hacked implentation, on offscreen maps)
        if (is_cutscene):
            return


        if (self.active):

            # For the level editor, chiefly
            if (show_frame):

                r = self.get_scaled_rect(scale = scale)

                window_controller.get_geometry_controller().draw_rect_frame(sx + r[0], sy + r[1], r[2], r[3], (196, 14, 38), 2)


            # Alarm triggers will render a "laser" when in game mode...
            if (not is_editor):

                if (self.behavior == TRIGGER_BEHAVIOR_ALARM):

                    r = self.get_rect(is_editor)

                    window_controller.get_geometry_controller().draw_rect(sx + r[0], sy + r[1], r[2], r[3], (200 + random.randint(-20, 20), 25, 25, 0.5 + (random.random() * 0.4)))


            # also for the editor only
            if (show_name):

                (cx, cy) = (
                    sx + (self.x * TILE_WIDTH) + ( int(self.width * TILE_WIDTH) / 2),
                    sy + (self.y * TILE_HEIGHT) + ( int(self.height * TILE_HEIGHT) / 2)
                )

                arrow_size = 16

                (x, y) = (
                    cx - (arrow_size / 2),
                    cy - 20
                )

                window_controller.get_default_text_controller().render(self.name, cx - int(window_controller.get_default_text_controller().get_text_renderer().size(self.name) / 2), cy - 10, (225, 225, 225))


            #return


            # Used for user-activated triggers
            if ( (self.advertisement_tooltip or self.show_prompt or (self.prompt_tooltip and self.prompt_tooltip.is_visible())) and (not is_cutscene) ):

                # If we aren't supposed to "show" the prompt (not hovering), then let's hurry up
                # and finish fading the thing away...
                if (not self.show_prompt):

                    # Do we even have a prompt tooltip (yet?)?
                    if (self.prompt_tooltip):

                        self.prompt_tooltip.darken()

                        # Once it's gone, we might want to show an advertisement
                        if (not self.prompt_tooltip.is_visible()):

                            # Do we have an advertisement to show?
                            if (self.advertisement_tooltip):

                                self.advertisement_tooltip.lighten()

                    # If we don't have / haven't created a prompt tooltip, just go ahead and try to show the advertisement...
                    elif (self.advertisement_tooltip):

                        self.advertisement_tooltip.lighten()

                # On the other hand, if we do want to see it, let's make sure it fades all the way in...
                else:

                    # If we have an advertisement, we might need to dismiss it first...
                    if (self.advertisement_tooltip):

                        # Fade away the advertisement
                        self.advertisement_tooltip.darken()

                        # Gone yet?
                        if (not self.advertisement_tooltip.is_visible()):

                            self.prompt_tooltip.lighten()

                    # Otherwise, just show the prompt right away...
                    else:
                        self.prompt_tooltip.lighten()

                r = self.get_rect(is_editor)

                (cx, y) = (
                    sx + r[0] + ( int(self.width * TILE_WIDTH) / 2),
                    sy + r[1]
                )

                arrow_size = 8

                (ax, ay) = (
                    cx - (arrow_size / 2),
                    y - arrow_size
                )

                if (self.leading_entity):

                    (ax, ay) = (
                        ax,
                        sy + self.leading_entity.get_y() - arrow_size
                    )

                # Render prompt?
                if ( (self.prompt_tooltip) and (self.prompt_tooltip.is_visible()) ):

                    widget = self.prompt_tooltip.get_widget()

                    if (widget):

                        window_controller.get_geometry_controller().draw_triangle(ax, ay, arrow_size, arrow_size, (225, 225, 225, self.prompt_tooltip.alpha_controller.get_interval()), (40, 137, 225, self.prompt_tooltip.alpha_controller.get_interval()), DIR_DOWN)

                        (tooltip_width, tooltip_height) = (
                            self.prompt_tooltip.get_widget().get_width(),
                            self.prompt_tooltip.get_widget().get_render_height(text_renderer)
                        )

                        # Define a wrapper for the prompt text
                        r = (cx - int(tooltip_width / 4), ay - tooltip_height - arrow_size + 0, tooltip_width, tooltip_height)

                        # Make sure the tooltip renders easily within the viewing area
                        if (r[0] < 24):
                            r = offset_rect(r, (24 - r[0]), 0)

                        elif ( (r[0] + r[2]) > (SCREEN_WIDTH - 24) ):
                            r = offset_rect(r, (SCREEN_WIDTH - 24) - (r[0] + r[2]), 0)

                        self.prompt_tooltip.render(r[0], r[1], None, additional_sprites, window_controller.get_default_text_controller().get_text_renderer(), window_controller)

                # Render advertisement
                elif ( (self.advertisement_tooltip) and (self.advertisement_tooltip.is_visible()) ):

                    """
                    window_controller.get_geometry_controller().draw_triangle(ax, ay, arrow_size, arrow_size, (225, 225, 225, self.advertisement_tooltip.alpha_controller.get_interval()), (40, 137, 225, self.advertisement_tooltip.alpha_controller.get_interval()), DIR_DOWN)


                    self.advertisement_tooltip.do_shrinkwrap( window_controller.get_default_text_controller().get_text_renderer() )

                    # x/y padding for the prompt within its background
                    text_padding = (15, 0)

                    (tooltip_width, tooltip_height) = (
                        self.advertisement_tooltip.get_widget().width,
                        self.advertisement_tooltip.get_widget().get_render_height( window_controller.get_default_text_controller().get_text_renderer() )
                    )

                    # Define a wrapper for the prompt text
                    r = (cx - int(tooltip_width / 4) - text_padding[0], ay - tooltip_height - text_padding[1] - arrow_size, tooltip_width + (2 * text_padding[0]), (tooltip_height + (2 * text_padding[1])))

                    # Make sure the tooltip renders easily within the viewing area
                    #if (r[0] < 24):
                    #    r = offset_rect(r, (24 - r[0]), 0)

                    #elif ( (r[0] + r[2]) > (SCREEN_WIDTH - 24) ):
                    #    r = offset_rect(r, (SCREEN_WIDTH - 24) - (r[0] + r[2]), 0)

                    self.advertisement_tooltip.render(r[0], r[1], None, additional_sprites, window_controller.get_default_text_controller().get_text_renderer(), window_controller)
                    """

                    widget = self.advertisement_tooltip.get_widget()

                    if (widget):

                        window_controller.get_geometry_controller().draw_triangle(ax, ay, arrow_size, arrow_size, (225, 225, 225, self.advertisement_tooltip.alpha_controller.get_interval()), (40, 137, 225, self.advertisement_tooltip.alpha_controller.get_interval()), DIR_DOWN)

                        (tooltip_width, tooltip_height) = (
                            self.advertisement_tooltip.get_widget().get_width(),
                            self.advertisement_tooltip.get_widget().get_render_height(text_renderer)
                        )

                        # Define a wrapper for the advertisement text
                        r = (cx - int(tooltip_width / 4), ay - tooltip_height - arrow_size + 0, tooltip_width, tooltip_height)

                        # Make sure the tooltip renders easily within the viewing area
                        if (r[0] < 24):
                            r = offset_rect(r, (24 - r[0]), 0)

                        elif ( (r[0] + r[2]) > (SCREEN_WIDTH - 24) ):
                            r = offset_rect(r, (SCREEN_WIDTH - 24) - (r[0] + r[2]), 0)

                        self.advertisement_tooltip.render(r[0], r[1], None, additional_sprites, window_controller.get_default_text_controller().get_text_renderer(), window_controller)

            elif ( (not self.show_prompt) and (not is_cutscene) and (not is_editor) and (self.advertisement != "") ):

                # If the "activation prompt" tooltip remains visible, clear it away first...
                if ( (self.prompt_tooltip) and ( self.prompt_tooltip.is_visible() ) ):

                    self.prompt_tooltip.darken()

                else:

                    (cx, y) = (
                        sx + (self.x * TILE_WIDTH) + ( int(self.width * TILE_WIDTH) / 2),
                        sy + (self.y * TILE_HEIGHT)
                    )

                    arrow_size = 8

                    (ax, ay) = (
                        cx - (arrow_size / 2),
                        y - arrow_size
                    )

                    window_controller.get_geometry_controller().draw_triangle(ax, ay, arrow_size, arrow_size, (225, 225, 225), (40, 137, 225), DIR_DOWN)

                    # Calculate text width
                    text_width = window_controller.get_default_text_controller().get_text_renderer().size(self.advertisement)

                    # x/y padding for the prompt within its background
                    text_padding = (5, 1)

                    # Define a wrapper for the prompt text
                    r = (cx - int(text_width / 2) - text_padding[0], ay - 25 - (2 * text_padding[1]), text_width + (2 * text_padding[0]), (25 + (2 * text_padding[1])))

                    window_controller.get_geometry_controller().draw_rounded_rect(r[0], r[1], r[2], r[3], (25, 25, 25, 0.75), (225, 225, 225))

                    window_controller.get_default_text_controller().render(self.advertisement, cx - int(text_width / 2), ay - 25, (225, 225, 225))

            else:

                if (self.prompt_tooltip):
                    self.prompt_tooltip.darken()
