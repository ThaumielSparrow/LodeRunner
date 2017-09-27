from code.extensions.common import UITemplateLoaderExt

from code.tools.eventqueue import EventQueue

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import evaluate_spatial_expression, intersect, intersect_y, offset_rect, log, log2, xml_encode, xml_decode, set_alpha_for_rgb, coalesce

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_PROMPT_WIDTH, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_HOME, INPUT_SELECTION_END, INPUT_SELECTION_PAGEUP, INPUT_SELECTION_PAGEDOWN, INPUT_SELECTION_ACTIVATE, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, DATE_WIDTH, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIALOGUE_PANEL_WIDTH, DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE, LITERAL_POSITION_TRANSLATIONS, TOOLTIP_MIN_PADDING_X, TOOLTIP_MIN_PADDING_Y
from code.constants.common import STENCIL_MODE_NONE, STENCIL_MODE_PAINT, STENCIL_MODE_ERASE, STENCIL_MODE_PAINTED_ONLY, STENCIL_MODE_UNPAINTED_ONLY


class TooltipExt(UITemplateLoaderExt):

    def __init__(self):

        UITemplateLoaderExt.__init__(self)


        # Keep a widget that we'll use to render the tooltip's contents (text, icons, whatever)
        self.widget = None


        # Tooltip may respond to certain events
        self.event_queue = EventQueue()


        # Visible?
        self.visible = True

        # Tooltip width
        self.width = 210 # hard-coded default


        # Alignment
        self.align = "left"


        # Should the tooltip delay before appearing?
        self.delay = 0
        self.delay_interval = 0

        # Will it only appear for a certain length of time?
        self.lifespan = -1 # Default to forever
        self.lifespan_interval = 0


        # Cache preference
        self.prevent_caching = False

        # Icon preference
        self.show_icon = True


        # We can mark a tooltip as important or not important.  Important tooltips
        # make sure to show on the screen; unimportant tooltips (such as those belonging
        # to a widget we are actively dismissing) do not bother with such trivialties!
        self.important = True


        # Alpha tracking
        self.alpha_controller = IntervalController(
            interval = 0.0,
            target = 0.9,
            speed_in = 0.045,
            speed_out = 0.065
        )


        # Track the text of this tooltip...
        self.text = ""


    def configure(self, options):

        # Tooltip text
        if ( "text" in options ):

            # Track
            self.text = options["text"]

            # Make a note that we might want to process this text for special tooltips (e.g. puzzle room completion status messages, etc.)
            # Note that we'll want to do this BEFORE building the tooltip UI.
            self.event_queue.add(
                action = "parse-tooltip-text"
            )


        # Size
        if ( "width" in options ):
            self.width = int( options["width"] )

        # Alignment
        if ( "align" in options ):
            self.align = options["align"]


        # Miscellaneous options
        if ( "prevent-caching" in options ):
            self.prevent_caching = ( int( options["prevent-caching"] ) == 1 )

        if ( "show-icon" in options ):
            self.show_icon = ( int( options["show-icon"] ) == 1 )


        if ( "important" in options ):
            self.important = ( int( options["important"] ) == 1 )


        if ( "delay" in options ):

            self.delay = int( options["delay"] )
            self.delay_interval = self.delay

        if ( "lifespan" in options ):

            self.lifespan = int( options["lifespan"] )
            self.lifespan_interval = self.lifespan


        # The configuration has changed (presumably); let's add an event to recreate the tooltip UI
        self.event_queue.add(
            action = "build"
        )


        # For chaining
        return self


    # Configure the alpha controller.
    # This forwards configuration data to the widget itself.
    def configure_alpha_controller(self, options):

        # Cascade to the tooltip's widget stuff
        self.widget.configure_alpha_controller(options)


    # Callbacks
    def while_awake(self):

        # Not already awake?
        if (not self.visible):

            # Now we're visible
            self.visible = True

            # Full lifespan
            self.lifespan_interval = self.lifespan

            # Make sure we're fading in...
            self.configure_alpha_controller({
                "interval": 0,
                "target": 0.9
            })

            #log( "**tooltip waking up:  ", self, (self.alpha_controller.get_interval(), self.alpha_controller.get_target()) )


    def while_asleep(self):

        # Go to sleep?
        if (self.visible):

            # Fade it out at the standard fade rate
            self.configure_alpha_controller({
                "target": 0
            })

            # No longer visible
            self.visible = False

            #self.delay_interval = self.delay
            #self.alpha_controller.set_interval(0)

            #log( "**tooltip going to sleep:  ", self )

        # See if it's fully faded away?
        elif ( self.alpha_controller.get_interval() == 0 ):

            # Not anymore...
            self.visible = False

            # Clear alpha
            self.configure_alpha_controller({
                "interval": 0
            })

            # Reset lifespan tracker
            self.lifespan_interval = self.lifespan

            # Reset delay tracker
            self.delay_interval = self.delay


    # Get the RowMenu widget that we use to render the tooltip data
    def get_widget(self):

        return self.widget


    def set_widget(self, widget):

        self.widget = widget


    def lighten(self):

        self.alpha_controller.summon(target = 0.75)

        self.alpha_controller.process()


    def darken(self):

        self.alpha_controller.dismiss()

        self.alpha_controller.process()


    def is_visible(self):

        return ( self.alpha_controller.is_visible() )


    def do_shrinkwrap(self, text_renderer):

        log( "**???" )
        log( 5/0 )

        if (not self.shrinkwrapped):

            # Do we really need the default width?
            text_width = text_renderer.size(self.text, p_max_width = self.width)

            if ( (text_width + (2 * self.cellpadding)) < self.width):

                self.width = text_width + (2 * self.cellpadding)


            # We've checked for shrinkwrapping now...
            self.shrinkwrapped = True


    # Translate contents using a given hash
    def translate(self, h):

        # Validate widget exists
        if (self.widget):

            # Forward to widget
            self.widget.translate(h)


    # Classes that inherit this base type should override this to handle their events
    def handle_event(self, event, control_center, universe):

        return


    def process(self, control_center, universe):

        #print "**process me:  ", self

        # Does the event queue have any event available?
        while ( self.event_queue.has_events() ):

            # Handle next generic event
            self.handle_event(
                event = self.event_queue.fetch(),
                control_center = control_center,
                universe = universe
            )


        #print "**yo"
        # Is the widget visible?
        if ( (self.visible) or ( self.alpha_controller.is_visible() ) ):

            #print "**visible:  ", self.delay_interval, self.lifespan, self.lifespan_interval, " -> ", self.alpha_controller.get_interval(), self.alpha_controller.get_target()

            # Should we delay for a moment?
            if (self.delay_interval > 0):

                self.delay_interval -= 1

            # Process fade, etc...
            else:

                # Track lifespan, if applicable...
                if (self.lifespan >= 0):

                    if (self.lifespan_interval > 0):

                        self.lifespan_interval -= 1

                        # End of the line?
                        if (self.lifespan_interval <= 0):

                            # Fade it away...
                            self.alpha_controller.dismiss()


                # Process the widget
                if (self.widget):

                    #print "\t\t** Let's process widget"

                    self.widget.process(control_center, universe)


                # Process alpha
                self.alpha_controller.process()


    def render(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Have we created a RowMenu for this tooltip yet?
        if (self.widget):

            #print "\t\t**render me at:  ", r, "width = ", self.widget.get_width(), self.widget.width, self.width, self.alpha_controller.get_interval()

            # Render position
            (rx, ry) = (
                sx,         # We might translate...
                sy
            )


            # Handle "stay within screen bounds" logic for "important" tooltips (tooltips are important by default)
            if (self.important):

                # Don't let it go off the top of the screen...
                if (ry < TOOLTIP_MIN_PADDING_Y):

                    # If it's too tall it's too tall, but hey... we tried!
                    ry = TOOLTIP_MIN_PADDING_Y

                # Try not to let it go off the bottom of the screen, either...
                elif ( (ry + self.widget.get_render_height(text_renderer)) > (SCREEN_HEIGHT - TOOLTIP_MIN_PADDING_Y) ):

                    ry = ( (SCREEN_HEIGHT - TOOLTIP_MIN_PADDING_Y) - self.widget.get_render_height(text_renderer) )


            # Render tooltip widget
            self.widget.draw(rx, ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


class TriggerTooltip(TooltipExt):

    def __init__(self):

       TooltipExt.__init__(self)


    # React to an event
    def handle_event(self, event, control_center, universe):

        # Build UI?
        if ( event.get_action() == "build" ):

            # Fetch the widget dispatcher
            widget_dispatcher = control_center.get_widget_dispatcher()


            """
            # Create a RowMenu to hold the tooltip...
            self.widget = widget_dispatcher.create_row_menu().configure({
                "class": "tooltip",
                "width": self.width,
                "height": SCREEN_HEIGHT,
                "shrinkwrap": True,
                "global-frame": True,
                "uses-focus": False
            })
            """

            # Fetch the trigger tooltip template
            template = self.fetch_xml_template("trigger.tooltip", version = "normal").add_parameters({
                "@x": xml_encode( "0" ),
                "@y": xml_encode( "0" ),
                "@width": xml_encode( "%d" % self.width ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@content": xml_encode( "%s" % self.text ),
                "@cache-preference": xml_encode( "0" if (self.prevent_caching) else "1" )
            })

            """
            # Alternate, icon-free version...
            if (not self.show_icon):
            """

            if (0):
                xml = """
                    <item-group class = 'prompt' render-border = '1'>
                        <item>
                            <label x = '50%%' y = '0' width = '100%%' value = '%s' align = 'center' cache-preference = '1' />
                        </item>
                    </item-group>
                """ % xml_encode(self.text)

            # Compile the markup
            root = template.compile_node_by_id("tooltip")

            # Create the widget for this tooltip
            self.widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)


        # Parse text for special text replacement?
        elif ( event.get_action() == "parse-tooltip-text" ):

            # Special text markers indicate the need for an on-the-fly translation,
            # such as with puzzle / challenge rooms.
            if ( self.text.startswith("#puzzle:") or self.text.startswith("#challenge:") ):

                # Fetch the map name...
                (prefix, map_name) = self.text.split(":", 1)


                # Is the puzzle yet complete?
                if ( universe.is_map_completed(map_name) ):

                    self.text = "[color=normal]%s\nStatus:  [color=special]Complete![/color][/color]" % universe.get_map_title(map_name)

                # No?  Too bad...
                else:

                    # Did the player last use the keyboard for input?
                    if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ):

                        # Use keyboard translations
                        self.text = universe.translate_session_variable_references(
                            "[color=normal]%s\nDifficulty:  %s\nStatus:  [color=special]Incomplete[/color]\nPress [color=special]$[sys.input.keyboard.interact][/color] to enter[/color]." % ( universe.get_map_title(map_name), universe.get_map_data(map_name).get_difficulty() ),
                            control_center
                        )

                    # No; assume gamepad.
                    else:

                        # Use gamepad translations
                        self.text = universe.translate_session_variable_references(
                            "[color=normal]%s\nDifficulty:  %s\nStatus:  [color=special]Incomplete[/color]\nPress [color=special]$[sys.input.gamepad.interact][/color] to enter[/color]." % ( universe.get_map_title(map_name), universe.get_map_data(map_name).get_difficulty() ),
                            control_center
                        )

            else:

                # Don't do anything special to the text.  Just translate session variables.
                self.text = universe.translate_session_variable_references(self.text, control_center)


class RowMenuTooltip(TooltipExt):

    def __init__(self):

       TooltipExt.__init__(self)

       self.event_queue.add(
            action = "first-build"
        )

