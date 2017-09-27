#from code.extensions.common import UITemplateLoaderExt
from code.ui.containers.box import Box

from code.tools.eventqueue import EventQueue

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import evaluate_spatial_expression, intersect, intersect_y, offset_rect, log, log2, logn, xml_encode, xml_decode, set_alpha_for_rgb, coalesce

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_PROMPT_WIDTH, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_HOME, INPUT_SELECTION_END, INPUT_SELECTION_PAGEUP, INPUT_SELECTION_PAGEDOWN, INPUT_SELECTION_ACTIVATE, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, DATE_WIDTH, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIALOGUE_PANEL_WIDTH, DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE, LITERAL_POSITION_TRANSLATIONS, TOOLTIP_MIN_PADDING_X, TOOLTIP_MIN_PADDING_Y
from code.constants.common import STENCIL_MODE_NONE, STENCIL_MODE_PAINT, STENCIL_MODE_ERASE, STENCIL_MODE_PAINTED_ONLY, STENCIL_MODE_UNPAINTED_ONLY

# Local constant
TOOLTIP_ARROW_SIZE = 12

class Tooltip(Box):

    def __init__(self):

        Box.__init__(self, selector = "tooltip")


        # Track the parent widget
        self.parent = None


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


    # Configure Tooltip widget
    def configure(self, options):

        # Standard configuration
        Box.configure(self, options)


        # Parent widget
        if ( "parent" in options ):

            self.parent = options["parent"]


        # Tooltip text
        if ( "text" in options ):

            # Track
            self.text = options["text"]

            # Make a note that we might want to process this text for special tooltips (e.g. puzzle room completion status messages, etc.)
            # Note that we'll want to do this BEFORE building the tooltip UI.
            self.event_queue.add(
                action = "parse-tooltip-text"
            )


        """
        # Size
        if ( "width" in options ):
            self.width = int( options["width"] )
        """

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


        # For chaining
        return self


    # Alias
    def translate(self, h):
        self.translate_environment_variables(h)

    # Translate a given hash of environment variables
    def translate_environment_variables(self, h):

        logn( "tooltip", ("tooltip", self, h) )

        # Loop children
        for widget in self.get_child_widgets():

            # Do not descend into new namespaces
            if ( widget.get_namespace() == None ):

                # Translate child widget
                widget.translate_environment_variables(h)


        # This widget only contains other widgets; it will not translate
        # anything of its own self.


    # Callbacks
    def on_focus(self):

        # Standard Box on focus
        Box.on_focus(self)


        # Full lifespan
        self.lifespan_interval = self.lifespan

        # Reset delay tracker
        self.delay_interval = self.delay

        # Fade in
        self.configure_alpha_controller({
            "interval": 0,
            "target": 0.9
        })

        logn( "tooltip", "tooltip bloodline:  %s" % self.get_bloodline() )


    def on_blur(self):

        # Standard Box on blur
        Box.on_blur(self)


        # Fade it out at the standard fade rate
        self.configure_alpha_controller({
            "target": 0
        })


    # Summon the tooltip
    def lighten(self):

        # Make mostly opaque
        self.alpha_controller.summon(target = 0.75)

        # This function implicitly processes the alpha controller
        self.alpha_controller.process()


    # Dismiss the tooltip
    def darken(self):

        # Set to fade away
        self.alpha_controller.dismiss()

        # This function implicitly processes the alpha controller
        self.alpha_controller.process()


    def is_visible(self):

        return ( self.alpha_controller.is_visible() )


    # The Tooltip will first do its special fade processing.
    # If tooltip is visible, it will run standard Box processing.
    def process(self, control_center, universe):

        # Start with no events (assume faded out)
        results = EventQueue()


        # Is the widget visible?
        if ( (self.visible) or ( self.alpha_controller.is_visible() ) ):

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


                # Process tooltip (standard Box processing)
                results.append(
                    Box.process(self, control_center, universe)
                )


                # Process alpha
                self.alpha_controller.process()

        # Return events
        return results


    # The Tooltip widget overwrites the standard Box.draw() method.
    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_margin_top() + self.vslide_controller.get_interval()
        )

        # Tooltip dimensions
        (width, height) = (
            self.get_width(),
            self.get_render_height(text_renderer)
        )


        # Where to render the arrow?
        (ax, ay) = (
            0,          # We'll overwrite these soon...
            0
        )

        # Arrow orientation
        arrow_orientation = DIR_RIGHT


        # Align top?
        if ( self.align in ("top", "top-left") ):

            # Arrow on the bottom, at 25% of the width
            (ax, ay) = (
                rx + int(width / 4) - int(TOOLTIP_ARROW_SIZE / 2),
                ry - TOOLTIP_ARROW_SIZE
            )

            # Point down
            arrow_orientation = DIR_DOWN

            # Move up by Tooltip height
            ry -= ( self.get_box_height(text_renderer) + TOOLTIP_ARROW_SIZE )

        # Align top right?
        elif ( self.align == "top-right" ):

            # Point down
            arrow_orientation = DIR_DOWN

            # Move over by parent width...
            rx += self.parent.get_width()

            # ...then, move back by self width
            rx -= width


            # Arrow on the top, at 75% of the width
            (ax, ay) = (
                rx + int(0.75 * width) - int(TOOLTIP_ARROW_SIZE / 2),
                ry - TOOLTIP_ARROW_SIZE
            )


            # Move up by height
            ry -= ( self.get_box_height(text_renderer) + TOOLTIP_ARROW_SIZE )

        # Align left?
        elif ( self.align == "left" ):

            # Adjust render y to center on the parent
            ry += ( int(self.parent.get_render_height(text_renderer) / 2) - int(height / 2) )


            # Arrow on the right, centered vertically
            (ax, ay) = (
                rx - TOOLTIP_ARROW_SIZE,
                ry + int(height / 2) - int(TOOLTIP_ARROW_SIZE / 2)
            )


            # Don't go too high on the screen
            if (ry < PAUSE_MENU_Y):

                # Clamp
                ry = PAUSE_MENU_Y

            # Don't go too low on the screen
            elif ( (ry + height) > (SCREEN_HEIGHT - PAUSE_MENU_Y) ):

                # Clamp
                ry = (SCREEN_HEIGHT - PAUSE_MENU_Y) - height


            # Point right
            arrow_orientation = DIR_RIGHT

            # Adjust render x over by full self width
            rx -= (width + TOOLTIP_ARROW_SIZE)

        # Align right?
        elif ( self.align == "right" ):

            # Adjust render x by parent's entire width
            rx += self.parent.get_width()


            # Adjust render y to center on the parent
            ry += ( int(self.parent.get_render_height(text_renderer) / 2) - int(height / 2) )

            # Arrow on the left, centered vertically
            (ax, ay) = (
                rx,
                ry + int(height / 2) - int(TOOLTIP_ARROW_SIZE / 2)
            )


            # Don't go too high on the screen
            if (ry < PAUSE_MENU_Y):

                # Clamp
                ry = PAUSE_MENU_Y

            # Don't go too low on the screen
            elif ( (ry + height) > (SCREEN_HEIGHT - PAUSE_MENU_Y - 5) ):

                # Clamp
                ry = (SCREEN_HEIGHT - PAUSE_MENU_Y - 5) - height


            # Point left
            arrow_orientation = DIR_LEFT

            # Move render x over by arrow size
            rx += TOOLTIP_ARROW_SIZE


            logn( "tooltip", "tooltip:  ", (rx, ry), self.parent, self.parent.get_width() )





        # Now, render the border, if/a
        if (self.render_border):

            # Render border first
            self.__std_render_border__(rx, ry, width, height, window_controller)

            # Render frame (?)
            self.__std_render_frame__(rx, ry, width, height, window_controller)


        """
        #print stencil_controller.get_mode()
        # Render a fill behind the widget's contents?
        if (self.fill == "always"):

            self.__std_render_fill__(rx, ry, width, height, window_controller)
            #print self.get_bloodline()
            #print width, height, self.get_gradient_start(), self.get_gradient_end(), self.get_background_alpha(), self.alpha_controller.get_interval()

        elif ( (self.fill == "active") and ( self.is_focused() ) ):

            self.__std_render_fill__(rx, ry, width, height, window_controller)
        """

        # Calculate desired alpha for the tooltip arrow
        alpha = ( self.alpha_controller.get_interval() * self.get_background_alpha() )


        # Render tooltip arrow
        window_controller.get_geometry_controller().draw_triangle(ax, ay, TOOLTIP_ARROW_SIZE, TOOLTIP_ARROW_SIZE, set_alpha_for_rgb(alpha, self.get_gradient_start() ), set_alpha_for_rgb(alpha, self.get_border_color() ), orientation = arrow_orientation)

        # Base widget rendering position (accounting for box padding)
        (wx, wy) = (
            rx + self.get_padding_left(),
            ry + self.get_padding_top()
        )

        # Loop widgets
        for i in range( 0, len(self.widgets) ):

            # Convenience
            widget = self.widgets[i]

            # We'll only render the widget when appropriate...
            if ( (widget.display == "constant") or ( widget.display == "on-focus" and self.is_focused() ) or (widget.display == "on-focus:linger" and ( self.is_focused() or widget.linger() )) or (widget.display == "off-focus" and ( not self.is_focused() )) ):

                # Render widget
                widget.draw(wx, wy, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


        #window_controller.get_geometry_controller().draw_rect(rx, ry, self.get_width(), self.report_widget_height(text_renderer), (25, 25, 225, 0.25))

    """
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
    """
