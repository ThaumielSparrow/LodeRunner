import traceback

import os
import sys
import random
import time
import math

from code.ui.widget import Widget

from code.render.glfunctions import GLSpritesheet # used for UIGraphic
from code.render.textblaster import TextBlaster

from code.tools.eventqueue import EventQueue

from code.controllers.intervalcontroller import IntervalController

from code.game.universe import Universe

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, LAYER_FOREGROUND, LAYER_BACKGROUND, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, CAMERA_SPEED, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_ACTIVATE, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, DATE_WIDTH, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, TILE_HEIGHT, PAD_AXIS, PAD_HAT, PAD_BUTTON, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, GENUS_PLAYER, GENUS_ENEMY, DEFAULT_PLAYER_COLORS
from code.constants.common import INPUT_MOVE_UP, INPUT_MOVE_RIGHT, INPUT_MOVE_DOWN, INPUT_MOVE_LEFT, INPUT_SELECTION_ACTIVATE

from code.constants.states import STATUS_INACTIVE

from code.constants.common import INPUT_SELECTION_PAGEDOWN # Used while debugging worldmap travel navigation

from code.constants.paths import REPLAYS_PATH

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import intersect, offset_rect, log, log2, logn, xml_encode, xml_decode, set_alpha_for_rgb, rgb_to_glcolor, parse_rgb_from_string, evaluate_spatial_expression

from pygame.locals import K_ESCAPE, K_UP, K_DOWN 


# All widgets should inherit from this class.
# It sets barebones / empty versions of an assortment of universal callback functions.
class UIWidget(Widget):

    def __init__(self, selector = "no-selector"):

        Widget.__init__(self, selector)


        # Some widgets might react to being "poked."
        self.poked = False

        # Create an inbox that a widget can use to save poke data for future use (we handle this in on_poke() typically...)
        self.inbox = EventQueue()


        # We can assign "environment variables" to a widget.
        # We will translate these when we build the widget, but
        # we will perform localization beforehand.
        self.environment_variables = {}


    # Close, releasing any resource (gl asset, etc.) this widget
    # might be using.
    def close(self, control_center):

        # Loop child widgets
        for widget in self.get_child_widgets():

            # Close child
            widget.close(control_center)


    # Widgets have a standard set of state properties (focus state, bloodline, etc.)
    def save_state(self):

        # Create node
        root = XMLNode("widget")

        # Set root node properties
        root.set_attributes({
            "lock-count": xml_encode( "%d" % self.lock_count ),
            "class": xml_encode( self.css_class ),
            "state": xml_encode( self.css_state ),
            "bloodline": xml_encode( self.bloodline ),
            "is-focused": xml_encode( "%d" % int( self.is_focused() ) )
        })


        # Add a node for attributes
        node = root.add_node(
            XMLNode("attributes")
        )

        # Set attributes on the "attributes" node (what a hack)
        for key in self.attributes:

            node.set_attributes({
                key: xml_encode( "%s" % self.attributes[key] )
            })



        node = XMLParser().create_node_from_xml("""
            <widget>
                <attributes />
                <interval-controllers />
            </widget>
        """)


        # Add a node for interval controllers
        node = root.add_node(
            XMLNode("interval-controllers")
        )

        # Track the slide interval controllers
        node.add_nodes(
            (
                self.hslide_controller.get_state(),
                self.vslide_controller.get_state(),
                self.alpha_controller.get_state()
            )
        )


        # Lastly, we want to track the current CSS state.
        node = root.add_node(
            XMLNode("css")
        )

        # This is a pretty brutal hack job.  I wonder if I actually still use this stuff, even?  Maybe...
        node.add_nodes((

            XMLNode("margin-top").set_inner_text( "%s" % self.margin_top ),
            XMLNode("margin-bottom").set_inner_text( "%s" % self.margin_bottom ),

            XMLNode("padding-top").set_inner_text( "%s" % self.padding_top ),
            XMLNode("padding-right").set_inner_text( "%s" % self.padding_right ),
            XMLNode("padding-bottom").set_inner_text( "%s" % self.padding_bottom ),
            XMLNode("padding-left").set_inner_text( "%s" % self.padding_left ),

            XMLNode("border-size").set_inner_text( "%s" % self.border_size ),

            XMLNode("shadow-size").set_inner_text( "%s" % self.shadow_size )

        ))


        # Return the state-defining node
        return root


    # Widgets will globally perform a set of recall tasks upon state restore
    def load_state(self, node):

        # Go ahead and invalidate cached metrics
        self.invalidate_cached_metrics()


        # Validate we have a widget node
        if ( node.tag_type == "widget" ):

            # Restore lock count
            self.lock_count = int( node.get_attribute("lock-count") )

            # Grab css class / state
            self.css_class = node.get_attribute("class")
            self.css_state = node.get_attribute("state")

            # Recall bloodline
            self.configure({
                "bloodline": xml_decode( node.get_attribute("bloodline") )
            })
            #self.bloodline = node.get_attribute("bloodline")

            # Should this widget have focus?
            self.has_focus = ( int( node.get_attribute("is-focused") ) == 1 )


            # Check custom-assigned attributes
            attributes_node = node.get_first_node_by_tag("attributes")

            for key in attributes_node.get_attributes():

                self.set_attribute(
                    key, xml_decode( attributes_node.get_attribute(key) )
                )


            # Update slide interval controllers
            self.hslide_controller.set_state(
                node.get_first_node_by_tag("interval-controllers").get_nodes_by_tag("interval-controller")[0]
            )

            self.vslide_controller.set_state(
                node.get_first_node_by_tag("interval-controllers").get_nodes_by_tag("interval-controller")[1]
            )

            # Update alpha interval controller
            self.alpha_controller.set_state(
                node.get_first_node_by_tag("interval-controllers").get_nodes_by_tag("interval-controller")[2]
            )


            # Add the end here, let's lastly load in the css state data
            css_node = node.get_first_node_by_tag("css")

            # Validate
            if (css_node):

                style_collection = css_node.get_nodes_by_tag("*")

                for ref_style in style_collection:

                    self.css({
                        "%s" % ref_style.tag_type: "%s" % ref_style.innerText
                    })


            # If the widget has focus, call .focus() to make sure CSS is up-to-date
            if ( self.is_focused() ):

                self.focus()

            else:

                self.blur()

        # Not the right type of param
        else:
            log( "Invalid state node provided" )


    # Alias
    def translate(self, h):
        self.translate_environment_variables(h)

    # Translate environment variables using a given hash
    def translate_environment_variables(self, h):

        # By default, a widget does not support translation.
        # Overwrite in inheriting classes for each each.
        return


    def handle_user_input(self, control_center, universe):

        # Return an empty event queue by default
        return EventQueue()


    # Event callbacks
    def handle_birth(self):

        return EventQueue()


    def on_resize(self, text_renderer = None):

        pass

    # By default, return nothing on select...
    def on_select(self):

        return None


    # Poke a widget to see if it responds
    def poke(self):

        # Flag
        self.poked = True

        # Callback with params
        self.on_poke()


    # On poke callback
    def on_poke(self):

        # Poke each child widget
        for widget in self.get_child_widgets():

            # Poke
            widget.poke()


    # Add environment variables using a hash
    def add_environment_variables(self, h):

        # Update known variables
        self.environment_variables.update(h)


    # Get environment variables hash
    def get_environment_variables(self):

        # Return hash
        return self.environment_variables


    # Translate a given hash of environment variables
    def translate_environment_variables(self, h):

        # Default action; overwrite in inheriting widgets
        return


    # A default widget will never find a widget within itself.  Widgets can overwrite
    # this method to implement that functionality.
    def find_widget_by_id(self, widget_id):

        return None


class Label(UIWidget):

    def __init__(self):#, width, universe, session, node):#, align = None):

        UIWidget.__init__(self, selector = "label")


        # Text the label will display
        self.text = ""

        # A label's text might have a special prefix (e.g. avatar:)
        # indicating that this label should show an image only.
        self.working_texture = None


        # Perhaps we use a custom font?
        self.font = None

        # Labels can choose to employ a text blaster effect
        self.text_blaster = None

        # We can choose to reset the text blaster on blur
        self.reset_text_blaster_on_blur = False

        # It doesn't fully set up the text blaster effects until the first rendering pass, though.
        self.is_text_blaster_ready = False


        # Track active status
        self.awake = False


        # Alignment
        self.align = "left"

        # Vertical alignment
        self.valign = "top" # top, center, bottom


        # Inner text alignment (typically unused; I typically just use "align" unless I expect .width to change dynamically (e.g. HMenu))
        self.text_align = "left"


        # Should the label obey focus/linger commands, or simply remain visible permanently after fading in?
        self.obeys_linger_commands = True


        # Do we want to cache the text in this label?
        self.cache_preference = False

        # If we did cache the text, has it since become invalidated?
        # Default this to True on new elements.  This way, if it's using
        # a duplicate key (e.g. newsfeeder-generic), it "wins" and updates
        # the cache with its text.
        self.cache_invalidated = True

        # Generate a "random" cache key
        self.cache_key = "label-%s" % (random.random() * random.random())


        # Default to this color
        #self.color = (210, 210, 210)

        # May have a gradient
        self.color2 = None


        # A label can choose to display its contents as a scrolling marquee.
        # To enable this, assign a nonzero marquee rate.
        self.marquee_rate = 0

        # Current marquee offset
        self.marquee_dx = 0

        # Delay before marquee begins
        self.marquee_delay = 60
        self.marquee_delay_max = self.marquee_delay

        # Delay before marquee reset to beginning after scrolling stops
        self.marquee_delay_end = 30
        self.marquee_delay_end_max = self.marquee_delay_end


        # A label can specify alpha factors for the left / right end of the string
        self.alpha_factor_start = 1.0
        self.alpha_factor_end = 1.0


    # When closing the widget, we should delete the texture
    # if this label is using one.
    def close(self, control_center):

        # Standard close logic
        UIWidget.close(self, control_center)

        # Check for working texture id
        if (self.working_texture != None):

            # Delete texture
            control_center.get_window_controller().get_gfx_controller().delete_texture(self.working_texture)

            # Certainty
            logn( "textures", "Goodbye, label working texture (%s)" % self.working_texture )
            self.working_texture = None


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "value" in options ):
            self.set_text( options["value"] )

        if ( "font" in options ):
            self.font = options["font"]


        # Hard-coded, non-random cache key available?
        if ( "cache-key" in options ):

            # We definitely want the cache, then...
            self.cache_preference = True

            # Store given cache key
            self.cache_key = options["cache-key"]


        if ( "align" in options ):
            self.align = options["align"]

        if ( "valign" in options ):
            self.valign = options["valign"]


        if ( "text-align" in options ):
            self.text_align = options["text-align"]


        if ( "cache-preference" in options ):
            self.cache_preference = ( options["cache-preference"] == "1" )


        if ( "color" in options ):

            rgb = options["color"].split(",")

            if (len(rgb) == 3):

                self.color = (
                    int( rgb[0].strip() ),
                    int( rgb[1].strip() ),
                    int( rgb[2].strip() )
                )

        if ( "color2" in options ):

            rgb = options["color2"].split(",")

            if (len(rgb) == 3):

                self.color2 = (
                    int( rgb[0].strip() ),
                    int( rgb[1].strip() ),
                    int( rgb[2].strip() )
                )


        if ( "alpha-factor-start" in options ):
            self.alpha_factor_start = float( options["alpha-factor-start"] )

        if ( "alpha-factor-end" in options ):
            self.alpha_factor_end = float( options["alpha-factor-end"] )


        # Marquee rate?
        if ( "marquee-rate" in options ):
            self.marquee_rate = float( options["marquee-rate"] )


        if ( "text-effect" in options ):

            # Which effect to use?
            effect = options["text-effect"]

            # How many frames will it last?
            duration = 20

            # Overwrite duration?
            if ( "text-effect-duration" in options ):

                duration = int( options["text-effect-duration"] )


            # Initialize text blaster; we'll have to wait for the first rendering loop to set up the fade values, though.
            self.text_blaster = TextBlaster(self.text, max_width = self.get_width(), letters_per = 5, effect = effect, duration = duration, lag = 5, repeat_threshold = 25)


            # Will we want to reset the text blaster on blur?
            if ( "reset-on-blur" in options ):
                self.reset_text_blaster_on_blur = ( int( options["reset-on-blur"] ) == 1 )


        # Obey linger logic, or remain visible permanently?
        if ( "obeys-linger-commands" in options ):
            self.obeys_linger_commands = ( options["obeys-linger-commands"] == "1" )


        # For chaining
        return self


    # Set label text
    def set_text(self, text):

        # The text may change; reset cached metrics
        self.invalidate_cached_metrics()

        #"""
        # We must also invalidate cached metrics on any
        # parent widget.
        widget = self.get_top_parent()

        # Validate
        if (widget):

            widget.invalidate_cached_metrics()
        #"""


        # Save text
        self.text = xml_decode(text)


        # Invalidate cache so that we can keep the display up-to-date
        if (self.cache_preference == True):

            self.cache_invalidated = True


    # Get label text
    def get_text(self):

        return self.text



    # Alias
    def translate(self, h):
        self.translate_environment_variables(h)

    # Translate environment variables using a given hash
    def translate_environment_variables(self, h):

        # Store current text
        s = self.get_text()

        # Loop key/value pairs
        for (key, value) in [ (key, h[key]) for key in h ]:

            # Replace current text data
            s = s.replace(key, value)

        # Set new text
        self.set_text(s)


    # Start text blaster on focus
    def on_focus(self):

        # Standard UIWidget on focus
        UIWidget.on_focus(self)

        if (self.text_blaster):

            if (self.is_text_blaster_ready):

                self.text_blaster.activate()


    # Dismiss text blaster on blur
    def on_blur(self):

        # Standard UIWidget on blur
        UIWidget.on_blur(self)

        if (self.obeys_linger_commands):

            if (self.text_blaster):

                if (self.is_text_blaster_ready):

                    if (self.reset_text_blaster_on_blur):

                        self.text_blaster.reset()


    # Event callbacks
    def while_awake(self):

        if (self.text_blaster):

            if (self.is_text_blaster_ready):

                if (self.reset_text_blaster_on_blur):

                    if (not self.awake):

                        self.awake = True
                        self.text_blaster.activate()


    def while_asleep(self):

        if (self.text_blaster):

            if (self.is_text_blaster_ready):

                if (self.reset_text_blaster_on_blur):

                    if (self.awake):

                        self.awake = False
                        self.text_blaster.reset()


    def get_text_height(self, text_renderer):

        # Try to get cached version
        metric = self.get_cached_metric("text-height")

        # Validate
        if (metric != None):

            # Return
            return metric

        # Compute, then cache...
        else:

            # A marquee label always stays on one single line
            if (self.marquee_rate > 0):

                # 1 line
                metric = text_renderer.font_height

            # Other labels check for wordwrap
            else:

                # Compute
                metric = ( ( text_renderer.wrap_lines_needed( self.text, max_width = self.get_width() ) ) * text_renderer.font_height )
                logn( "metrics", "\nText:  %s\nHeight:  %s\n\n" % ( self.text[0:60], metric ) )


            # Cache
            self.cache_metric("text-height", metric)

            # Return
            return metric


    # Return the width of the text in this label
    def report_widget_width(self, text_renderer):

        # Try to get cached version
        metric = self.get_cached_metric("render-width")

        # Validate
        if (metric != None):

            # Return
            return metric

        # Compute, then cache...
        else:

            # Compute
            metric = 0


            # A marquee label always stays on one single line
            if (self.marquee_rate > 0):

                # 1 line
                metric = self.get_width()

            # Other labels check for wordwrap
            else:

                # Word wrap
                lines = text_renderer.wordwrap_text( self.text, 0, 0, (225, 225, 225), max_width = self.get_width() )

                # Content?
                if ( len(lines) > 0 ):

                    metric = max( o["width-used"] for o in lines )


            # Cache
            self.cache_metric("render-width", metric)

            # Return
            return metric


    # Return the height required for the raw text
    def report_widget_height(self, text_renderer):

        #print "label:  %d (%s) (width:  %d)" % (self.get_text_height(text_renderer), self.text, self.get_width())
        return self.get_text_height(text_renderer)


    def get_box_height(self, text_renderer):

        return UIWidget.get_box_height(self, text_renderer)


    def get_x_offset(self, text_renderer):

        if (self.align == "right"):

            #print "size:  ", text_renderer.size(self.text)
            return -text_renderer.size(self.text)

        else:

            return 0


    def get_max_x(self, text_renderer):

        if (self.align == "right"):

            return self.get_width()

        else:

            return ( self.get_x() + self.report_widget_width(text_renderer) )


    def linger(self):

        if (self.text_blaster):

            if (self.is_text_blaster_ready):

                return self.text_blaster.linger()

        return False


    def process(self, control_center, universe):#user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        if (self.text_blaster):

            if (self.is_text_blaster_ready):

                self.text_blaster.process()


        # Does this label use a marquee effect?
        if (self.marquee_rate > 0):

            # We need a handle to the text renderer
            text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


            # If marquee effect has not begun, check for initial delay.
            if ( (self.marquee_dx == 0) and (self.marquee_delay > 0) ):

                # Pause before beginning marquee
                self.marquee_delay -= 1

            # Continue marquee effect
            else:

                # Scroll
                self.marquee_dx -= self.marquee_rate

                # Get text width
                w = text_renderer.size(self.text)

                # Don't scroll beyond text's width
                if ( self.marquee_dx <= -w ):

                    # Clamp
                    self.marquee_dx = -w

                    # Decrease end delay
                    self.marquee_delay_end -= 1

                    # When delay ends, reset marquee to original position
                    if (self.marquee_delay_end <= 0):

                        # Reset all values
                        self.marquee_dx = 0
                        self.marquee_delay = self.marquee_delay_max
                        self.marquee_delay_end = self.marquee_delay_end_max


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        #(u, v) = (x, y)

        # If no working texture exists, we can check for
        # special text commands (e.g. avatar:) now.
        if (self.working_texture == None):

            # Check for "avatar:" command
            if (self.text[0:7] == "avatar:"):

                # The remainder of the command contains ssv data
                ssv = self.text[7:]

                # Separate the semicolon-separated values
                pieces = ssv.split(";")

                # Fetch sprite texture dimensions
                (w, h) = (
                    additional_sprites[GENUS_PLAYER]["simple"].get_texture_width(),
                    additional_sprites[GENUS_PLAYER]["simple"].get_texture_height()
                )

                # Replicate the unanimated (simple) player texture to begin the new working texture
                self.working_texture = window_controller.get_gfx_controller().clone_texture( additional_sprites[GENUS_PLAYER]["simple"].get_texture_id(), w, h )
                logn( "textures", "Hello label working texture (%s)" % self.working_texture )


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

                                # Implicitly add the "primary:bg" color, a downscaled (dimmed) copy of primary.
                                if (title == "primary"):

                                    # Add in a hidden color
                                    pieces.append("primary:bg=%s,%s,%s" % ( int(rgb[0] / 2), int(rgb[1] / 2), int(rgb[2] / 2) ))

                    # Loop
                    i += 1


        # Rendering position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            24,#self.get_width(),
            24#self.get_height(text_renderer)
        )

        # First, assume no letter fade percentages...
        letter_fade_percentages = []

        # But, if we have a text blaster effect chosen...
        if (self.text_blaster):

            # If it's not ready, then we need to initialize the fade values (so they fade in)
            if (not self.is_text_blaster_ready):

                self.text_blaster.setup_initial_fade_values(text_renderer)

                # Ready!
                self.is_text_blaster_ready = True


            # Get those fade percentages...
            letter_fade_percentages = self.text_blaster.get_letter_fade_values()


        # Default font
        text_controller = window_controller.get_default_text_controller()

        # Check for custom font
        if (self.font):

            text_controller = window_controller.get_text_controller_by_name(self.font)


        # Line offset?  (Defunct)
        margin_y = 0


        # Custom vertical alignment?
        if (self.valign == "center"):

            ry -= int( self.get_text_height(text_controller.get_text_renderer() ) / 2 )


        # On-the-fly text alignment
        if (self.text_align == "center"):

            rx += ( int( self.get_width() / 2 ) - int( text_renderer.size(self.text) / 2 ) )


        # Use our own widget alpha value
        alpha = self.alpha_controller.get_interval()


        if (self.cache_preference == True):

            # If we haven't cached this label yet (or it has somehow become invalidated), then
            # let's cache it right now.
            if ( ( not window_controller.cache_key_exists(self.cache_key) ) or (self.cache_invalidated) ):

                # Switch over to the common scratch pad to cache it
                window_controller.render_to_scratch_pad("common")

                # Render the text with wrap (to the common scratch pad).  Retrieve the portion of the screen we used to render the text.
                (texture_id, s, s) = text_renderer.render_and_clip_with_wrap(self.text, color = set_alpha_for_rgb(alpha, self.get_color()), max_width = self.get_width(), align = self.align, color_classes = self.get_bbcode(), letter_fade_percentages = letter_fade_percentages, window_controller = window_controller) # hard-coded colors!

                # Feed the "cached" screen area to the window controller's cache.
                window_controller.cache_texture_by_key(self.cache_key, texture_id, s, about = self.text)

                # Make sure we resume rendering ot the primary framebuffer
                window_controller.render_to_primary()


                # Cache is not currently invalidated
                self.cache_invalidated = False


            # Now that we have ensured that the label is cached, let's render from cache
            window_controller.render_cache_item_by_key(self.cache_key, rx, margin_y + ry)

            """            
            cache_item = text_controller.get_cache_item(self.cache_key)
            #print (self.cache_key, self.cache_preference, cache_item, self.cache_invalidated)
            if (cache_item and (not self.cache_invalidated)):
                cache_item.render(x, margin_y + y, glcolor = (1, 1, 1, alpha), window_controller = window_controller)
            else:
                #text_renderer.render_with_wrap(self.text, x, margin_y + y, set_alpha_for_rgb(alpha, color), max_width = self.get_width(), align = self.align, color_classes = color_classes, letter_fade_percentages = letter_fade_percentages, cache_key = self.cache_key)
                text_controller.render_with_wrap(self.text, x, margin_y + y, set_alpha_for_rgb(alpha, self.get_color()), max_width = self.get_width(), align = self.align, color_classes = self.get_bbcode(), letter_fade_percentages = letter_fade_percentages, cache_key = self.cache_key)
                # At this point, we've updated the cache (in the event that it had been invalidated)
                self.cache_invalidated = False
            """

        # If we have a working texture, we'll render it
        # instead of the text command.
        elif (self.working_texture != None):

            window_controller.get_gfx_controller().draw_sprite(rx, ry, 24, 24, additional_sprites[GENUS_PLAYER]["simple"], scale = 1.0, gl_color = (1.0, 1.0, 1.0, alpha), frame = 0, hflip = False, working_texture = self.working_texture)

        # Render text
        else:

            # We might need the scissor controller here
            scissor_controller = window_controller.get_scissor_controller()

            # Should we apply a scissor region for marquee scroll?
            if (self.marquee_rate > 0):

                # Set scissor
                scissor_controller.push( (rx, ry, self.get_width(), text_renderer.font_height) )

                # Offset render position by marquee value (marquee is always <= 0)
                rx += self.marquee_dx
                rx = int(rx)



            if ( (not self.color2) and (self.alpha_factor_start == self.alpha_factor_end) ):

                text_controller.render_with_wrap(self.text, rx, margin_y + ry, set_alpha_for_rgb( alpha, self.get_color() ), max_width = self.get_width(), align = self.align, color_classes = self.get_bbcode(), letter_fade_percentages = letter_fade_percentages)

                #window_controller.get_geometry_controller().draw_rect(x, y, 200, text_renderer.font_height, (25, 225, 25, 0.25))
                #window_controller.get_geometry_controller().draw_rect(x, margin_y + y, 200, text_renderer.font_height, (25, 25, 225, 0.25))
                #text_controller.render_with_wrap("%d, %s, %s" % (self.get_width(), self.get_width(), self.max_width), x, y, (225, 225, 25, 0.5))

            elif ( (not self.color2) and (self.alpha_factor_start != self.alpha_factor_end) ):

                text_controller.render(self.text, rx, margin_y + ry, p_color = set_alpha_for_rgb(self.alpha_factor_start * alpha, self.get_color()), p_color2 = set_alpha_for_rgb(self.alpha_factor_end * alpha, self.get_color()), p_align = self.align, color_classes = self.get_bbcode(), letter_fade_percentages = letter_fade_percentages)

            elif (self.color2):

                text_controller.render(self.text, rx, margin_y + ry, p_color = set_alpha_for_rgb(alpha, self.get_color()), p_color2 = (self.color2[0], self.color2[1], self.color2[2], alpha), p_align = self.align, color_classes = self.get_bbcode(), letter_fade_percentages = letter_fade_percentages)



            # Should we remove an active scissor region?
            if (self.marquee_rate > 0):

                # Remove last scissor region
                scissor_controller.pop()

        #window_controller.get_geometry_controller().draw_rect(u, v, 100, self.report_widget_height(text_renderer), (225, 225, 25, 0.5))
        #window_controller.get_geometry_controller().draw_rect(u + 25, v, 200, self.get_box_height(text_renderer), (225, 225, 25, 0.25))


class Action(UIWidget):

    def __init__(self):

        UIWidget.__init__(self)


        # An action must keep track of the parameters it will return when activated
        self.activation_params = {}


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Always force x / y / width / height of this widget to 0.
        # We might use width/height as attributes (e.g. for a popup),
        # and we don't want them applying to this invisible widget!
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0


        # Save all option attributes as action attributes
        for key in options:

            # Track it
            self.activation_params[key] = options[key]


        # For chaining
        return self


    # Overwrite select callback
    def on_select(self):

        results = EventQueue()

        if ( "do" in self.activation_params ):

            results.add(
                action = self.activation_params["do"],
                params = self.activation_params # This also includes the "do," I guess...
            )

        return results
        #print self.get_attributes()

        #return self.get_attributes()


    def process(self, control_center, universe):#, user_input, system_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)

        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        """
        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        text_renderer.render_with_wrap(self.activation_params["do"], rx, ry, set_alpha_for_rgb( alpha, self.get_color() ), max_width = self.get_width(), align = "left", color_classes = self.get_bbcode(), letter_fade_percentages = [])

        if ("template-version" in self.attributes):

            text_renderer.render_with_wrap(self.activation_params["template-version"], rx, ry + text_renderer.font_height, set_alpha_for_rgb( alpha, self.get_color() ), max_width = self.get_width(), align = "left", color_classes = self.get_bbcode(), letter_fade_percentages = [])
        """

        return


class KeyListener(UIWidget):

    def __init__(self):

        UIWidget.__init__(self)


        # An listener must keep track of the parameters it will return when it "hears" a keypress
        self.activation_params = {}

        # Wait a few frames before accepting input to prevent double-clicks and stuff
        self.delay = 15

        # Once a listener "hears" a key, it stops listening any further
        self.awake = True

        # We can optionally configure a listener to listen forever
        self.listen_forever = False


    # Configure
    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "listen-forever" in options ):
            self.listen_forever = ( int( options["listen-forever"] ) == 1 )


        # Save all option attributes as action attributes
        for key in options:

            # Track it
            self.activation_params[key] = options[key]


        # We always reserve a place to track which key got pressed, also...
        self.activation_params["keypress"] = 0


        # For chaining
        return self


    # Disable processing of this key listener by setting
    # its "awake" flag to False.
    def disable(self):

        # Flag
        self.awake = False


    # Reset previous input value and bring it back online (awake)
    def reset(self):

        # Flag as awake
        self.awake = True

        # Clear input
        self.activation_params["keypress"] = 0


    def process(self, control_center, universe):#, user_input, system_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Delay in progress?
        if (self.delay > 0):

            # Wait briefly...
            self.delay -= 1

        # Nope; actively listen for input, if awake...
        elif (self.awake):

            # Fetch system input from input controller
            system_input = control_center.get_input_controller().get_system_input()


            # If we detect keyboard input, we'll return the key that the user pressed
            # along with any parameters specified by the original markup
            if ( len(system_input["keydown-keycodes"]) > 0 ):

                # Track the keycode
                self.activation_params["keycode"] = system_input["keydown-keycodes"][0]

                # Add a new event
                results.add(
                    action = self.activation_params["do"],
                    params = self.activation_params # This also includes the "do," I guess...
                )


                # Ignore any further keypress data, if we're not configure to listen forever...
                if (not self.listen_forever):

                    # Often, we only care about the first button press
                    self.awake = False


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        return


class GamepadListener(UIWidget):

    def __init__(self):

        UIWidget.__init__(self)


        # An listener must keep track of the parameters it will return when it "hears" a keypress
        self.activation_params = {}

        # Wait a few frames before accepting input to prevent double-clicks and stuff
        self.delay = 15

        # Once a listener "hears" a key, it stops listening any further
        self.awake = True


    # Configure
    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Save all option attributes as action attributes
        for key in options:

            # Track it
            self.activation_params[key] = options[key]


        # We always reserve a place to track which key got pressed, also...
        self.activation_params["gamepad-event"] = 0


        # For chaining
        return self


    def process(self, control_center, universe):#, user_input, system_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Delay in progress?
        if (self.delay > 0):

            # Wait briefly...
            self.delay -= 1

        # Nope; actively listen for input, if awake...
        elif (self.awake):

            # Fetch system input from input controller
            system_input = control_center.get_input_controller().get_system_input()

            if ( len(system_input["gamepad-events"]) > 0 ):

                # Supply the gamepad event object as the "gamepad-event" activation param; we'll need the entire structure...
                self.activation_params["gamepad-event"] = system_input["gamepad-events"][0]

                # Add a new event
                results.add(
                    action = self.activation_params["do"],
                    params = self.activation_params # This also includes the "do," I guess...
                )


                # Ignore any further gamepad input data 
                self.awake = False

            else:

                return None


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        return


class Rect(UIWidget):

    def __init__(self):#, width, height, color = (225, 225, 225), node = None):

        UIWidget.__init__(self, selector = "rect")


        # We can assign a "midpoint percentage" to a rectangle that triggers a gradient reversal (fade in to midpoint, fade out from midpoint to end)
        self.midpoint = None


        # Horizontal alignment
        self.align = "left" # left, center, right

        # Vertical alignment
        self.valign = "top" # top, center, bottom


        # Is the rectangle rounded?
        self.rounded = False

        # Rounded corner radius, if/a
        self.radius = 5


        # We can give rectangles an explicit color (a color that "defies" any css color)
        self.explicit_color = None


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "align" in options ):
            self.align = options["align"]

        if ( "valign" in options ):
            self.valign = options["valign"]

        if ( "midpoint" in options ):
            self.midpoint = float( options["midpoint"] )

        if ( "rounded" in options ):
            self.rounded = ( int( options["rounded"] ) == 1 )

        if ( "radius" in options ):
            self.radius = int( options["radius"] )

        if ( "explicit-color" in options ):
            self.explicit_color = parse_rgb_from_string( options["explicit-color"] )


        # For chaining
        return self


    # Simple rectangle height
    def report_widget_height(self, text_renderer):

        return self.get_height(text_renderer)


    def get_max_x(self, text_renderer):

        return ( self.get_x() + self.get_width() )


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results

    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + + self.get_margin_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width() - (self.get_padding_left() + self.get_padding_right()),
            self.get_height(text_renderer) - (self.get_padding_top() + self.get_padding_bottom())
        )

        # If either of our dimensions is 0 or less, we'll abandon right now...
        if ( (width <= 0) or (height <= 0) ):

            return

        else:

            if (self.align == "right"):
                rx -= width

            elif (self.align == "center"):
                rx -= int(width / 2)


            if (self.valign == "center"):
                ry -= int(height / 2)

            elif (self.valign == "bottom"):
                ry -= height


            # Use our own widget alpha value
            alpha = self.alpha_controller.get_interval()


            # Without a defined midpoint, we render a standard rectangle...
            if (self.midpoint == None):

                # Check for explicit color
                if (self.explicit_color):

                    window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                        rx,
                        ry,
                        width,
                        height,
                        set_alpha_for_rgb( alpha, self.explicit_color ),
                        set_alpha_for_rgb( alpha, self.explicit_color )
                    )

                # Nope; use the css color
                else:

                    if (self.rounded):

                        window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                            rx,
                            ry,
                            width,
                            height,
                            set_alpha_for_rgb( alpha, self.get_gradient_start() ),
                            set_alpha_for_rgb( alpha, self.get_gradient_end() ),
                            radius = self.radius
                        )

                    else:

                        window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                            rx,
                            ry,
                            width,
                            height,
                            set_alpha_for_rgb( alpha, self.get_gradient_start() ),
                            set_alpha_for_rgb( alpha, self.get_gradient_end() )
                        )

            # With a midpoint, we render 2 rectangles...
            else:

                # Based on the midpoint value (a percentage), determine the length of
                # the 2 rectangles we'll render...
                width_left = int( self.midpoint * width )

                # Complement.  This avoids weird rounding discrepancies.
                width_right = (width - width_left)


                # Render the pair of rectangles
                window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                    rx,
                    ry,
                    width_left,
                    height,
                    set_alpha_for_rgb( alpha, self.get_gradient_start() ),
                    set_alpha_for_rgb( alpha, self.get_gradient_end() )
                )

                window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                    rx + width_left,
                    ry,
                    width_right,
                    height,
                    set_alpha_for_rgb( alpha, self.get_gradient_end() ),
                    set_alpha_for_rgb( alpha, self.get_gradient_start() )
                )


class AnimatedRect(Rect):

    def __init__(self):

        Rect.__init__(self)


        # Track how much of the rectangle should be rendered.
        self.visibility_controller = IntervalController(
            interval = 1.0,
            target = 1.0,
            speed_in = 0.05,
            speed_out = 0.05
        )


    # Configure (based on a normal Rect)
    def configure(self, options):

        # Standard rect configure
        Rect.configure(self, options)


        # special configuration for animation
        if ( "visible-width" in options ):

            self.visibility_controller.configure({
                "target": float( options["visible-width"] )
            })


        # For chaining
        return self


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Standard rectangle processing
        results = Rect.process(self, control_center, universe)


        # Animate visible width as necessary
        self.visibility_controller.process()


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width() - (self.get_padding_left() + self.get_padding_right()),
            self.get_height(text_renderer) - (self.get_padding_top() + self.get_padding_bottom())
        )

        # If either of our dimensions is 0 or less, we'll abandon right now...
        if ( (width <= 0) or (height <= 0) ):

            return

        elif ( self.visibility_controller.get_interval() < 0 ):

            return

        else:

            # Determine how much we need to clip from the end of the rectangle (if any)
            if ( self.visibility_controller.get_interval() < 1 ):

                # Fetch the scissor controller
                scissor_controller = window_controller.get_scissor_controller()


                # Calculate the actual width we'll show.  Multiply by a float to ensure we always use decimal precision.
                adjusted_width = int( self.visibility_controller.get_interval() * float(width) )

                #print adjusted_width

                # Set a scissor to prevent rendering beyond the visible region
                scissor_controller.push( (rx, ry, adjusted_width, height) )

                # Standard rectangle draw
                Rect.draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

                # Disable the scissor test we added
                scissor_controller.pop()

            # If no clipping is necessary, we draw the rectangle normally
            else:

                # Standard rectangle draw
                Rect.draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


# A VolumeRect works just like a normal rect, except that we can
# specify a percentage (i.e. a volumn from 0 - 100), and we render
# using multiple thin rectangles across the entire span.
class VolumeRect(Rect):

    def __init__(self):

        Rect.__init__(self)


        # Track how much of the rectangle should be rendered (0.0 - 1.0)
        self.volume = 1.0


        # Track the size of each rectangle slice
        self.slice_width = 4

        # Track the padding between each slice
        self.slice_padding = 2


    # Configure (based on a normal Rect)
    def configure(self, options):

        # Standard rect configure
        Rect.configure(self, options)


        # Update volume
        if ( "volume" in options ):

            # Update
            self.volume = float( options["volume"] )


            # Sanity
            if ( self.volume < 0 ):
                self.volume = 0
            elif ( self.volume > 1.0 ):
                self.volume = 1.0


        if ( "slice-width" in options ):
            self.slice_width = int( options["slice-width"] )

        if ( "slice-padding" in options ):
            self.slice_padding = int( options["slice-padding"] )



        # For chaining
        return self


    # Get current volume level
    def get_volume(self):

        # Return
        return self.volume


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Standard rectangle processing
        results = Rect.process(self, control_center, universe)

        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width() - (self.get_padding_left() + self.get_padding_right()),
            self.get_height(text_renderer) - (self.get_padding_top() + self.get_padding_bottom())
        )


        # Align center?
        if (self.align == "center"):

            # Offset by half width
            rx -= int(width / 2)

        # Align right?
        elif (self.align == "right"):

            # Offset by full width
            rx -= width


        # If either of our dimensions is 0 or less, we'll abandon right now...
        if ( (width <= 0) or (height <= 0) ):

            return

        else:

            # Use local alpha data
            alpha = self.alpha_controller.get_interval()


            # First, let's render all slices with a dim color
            for i in range( 0, width, (self.slice_width + self.slice_padding) ):

                # Calculate slice rendering location
                (slice_x, slice_y) = (
                    rx + i,
                    ry
                )

                # Assume full slice width
                slice_width = self.slice_width

                # Don't exceed total rect width on the final slice, though
                if ( (slice_x + slice_width) > (rx + width) ):

                    # Clamp
                    slice_width = ( (rx + width) - slice_x )


                # Render dim slice
                window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                    slice_x,
                    slice_y,
                    slice_width,
                    height,         # Always full height
                    set_alpha_for_rgb( alpha, self.get_gradient_start() ),
                    set_alpha_for_rgb( alpha, self.get_gradient_start() )
                )


            # Fetch the scissor controller
            scissor_controller = window_controller.get_scissor_controller()

            # Now set a scissor boundary according to this rect's volume level
            scissor_controller.push(
                (rx, ry, int( self.volume * float(width) ), height)
            )


            # Run the previous loop one more time, except we're using the "gradient end" color
            for i in range( 0, width, (self.slice_width + self.slice_padding) ):

                # Calculate slice rendering location
                (slice_x, slice_y) = (
                    rx + i,
                    ry
                )

                # Assume full slice width
                slice_width = self.slice_width

                # Don't exceed total rect width on the final slice, though
                if ( (slice_x + slice_width) > (rx + width) ):

                    # Clamp
                    slice_width = ( (rx + width) - slice_x )


                # Render dim slice
                window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                    slice_x,
                    slice_y,
                    slice_width,
                    height,         # Always full height
                    set_alpha_for_rgb( alpha, self.get_gradient_end() ),
                    set_alpha_for_rgb( alpha, self.get_gradient_end() )
                )


            # Disable the scissor test we added
            scissor_controller.pop()


# Hidden widget used only to store data
class Hidden(UIWidget):

    def __init__(self):#, width, height, color = (225, 225, 225), node = None):

        UIWidget.__init__(self, selector = "hidden")


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # For chaining
        return self


    # Simple rectangle height
    def report_widget_height(self, text_renderer):

        return 0


    def get_max_x(self, text_renderer):

        return 0


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results

    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Hidden widget
        return


class Icon(UIWidget):

    def __init__(self):#, index = 0, node = None):

        UIWidget.__init__(self, selector = "icon")


        # Icon index (on icon tilesheet)
        self.index = 0

        # Width, height overwrites
        self.width = SKILL_ICON_WIDTH    # hard-coded
        self.height = SKILL_ICON_HEIGHT

        # Alignment
        self.align = "left"

        # Vertical alignment
        self.valign = "top" # top, center, bottom


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Tilesheet index
        if ( "index" in options ):
            self.index = int( options["index"] )

        # Do we have an explicit alignment setting?
        if ( "align" in options ):
            self.align = options["align"]

        # How about vertical alignment?
        if ( "valign" in options ):
            self.valign = options["valign"]


        if ( "bloodline" in options ):
            if (self.css_class == "debug1"):

                log( "** icon:\n\t", options )


        # For chaining
        return self


    # For now, icons have the same width as tiles
    def report_widget_width(self, text_renderer):

        return self.get_width()


    # For now, icons have the same height as tiles
    def report_widget_height(self, text_renderer):

        return self.get_height(text_renderer)


    def get_max_x(self, text_renderer):

        return ( self.get_x() + self.get_width() )


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)

        if ( self.css_class == "debug1" ):
            log( "Hey there!", self.has_focus )

        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Rendering position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            24,#self.get_width(),
            24#self.get_height(text_renderer)
        )

        # Alignment adjustment?
        if (self.align == "center"):

            rx -= int(width / 2)

        elif (self.align == "right"):

            rx -= width


        # Vertical alignment?
        if (self.valign == "center"):

            ry -= int(height / 2)


        # Explicit color?
        if (self.color):

            # Override parameter
            color = self.color


        # Use our own widget alpha value
        alpha = self.alpha_controller.get_interval()


        # Render
        window_controller.get_gfx_controller().draw_sprite(rx, ry, width, height, additional_sprites["iconset1"], frame = self.index, gl_color = rgb_to_glcolor( set_alpha_for_rgb( alpha, self.get_color() ) ))

        #window_controller.get_geometry_controller().draw_rect(u, v, 100, self.get_render_height(text_renderer), (25, 225, 25, 0.5))


class Gif(UIWidget):

    def __init__(self):#:, width, height, universe, session, xml):

        UIWidget.__init__(self, selector = "gif")

        # General info
        self.name = ""
        self.title = ""

        # Alignment
        self.align = "left"


        # GIFs live in their own little universe...
        self.universe = None

        # Track universe name for reload purposes
        self.universe_name = ""


        # Will we draw all maps, or just the active map?
        self.draw_all_maps = False

        # Should we render a clean background color behind the GIF?
        self.render_background = True


        # Keep a queue of events
        self.event_queue = EventQueue()


        # Maps for animated (scripted) skill previews
        self.map = None

        # This GIF might use a custom-color player character
        self.custom_avatar_data = None


        # Possible upgrades
        self.upgrades = []


        # Set up text blasters for data pertaining to the relevant upgrade available
        #self.text_blasters = self.setup_text_blasters( int(session["core.skills.%s" % self.name]["value"]) )


        # Is this skill locked?
        #self.locked = (session["core.skills.%s:locked" % self.name]["value"] == "1")
        self.locked = False


        # We'll need a dummy session for skill activations...
        self.dummy_session = None


        self.debug_ccr = None


        self.pre_process()


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Universe specified?  Queue it up...
        if ( "universe" in options ):

            # Keep track of universe name
            self.universe_name = options["universe"]

            self.event_queue.add(
                action = "load-universe"
            )

        # Default map?
        if ( "map" in options ):

            self.event_queue.add(
                action = "activate-map",
                params = {
                    "name": options["map"]
                }
            )

        # Set replay filepath?
        if ( "replay-file" in options ):

            self.event_queue.add(
                action = "load-replay-file",
                params = {
                    "replay-file": options["replay-file"]
                }
            )

        # Set an active skill for the "player" in this GIF?
        if ( "active-skill" in options ):

            self.event_queue.add(
                action = "set-active-skill",
                params = {
                    "active-skill": options["active-skill"]
                }
            )


        # Did the XML provide specific avatar color data?
        if ( "avatar-data" in options ):

            self.event_queue.add(
                action = "customize-avatar",
                params = {
                    "avatar-data": options["avatar-data"]
                }
            )
            """

            # Let's use it to colorify the player in the GIF
            self.custom_avatar_data = options["avatar-data"]


            # Find the player (always player1 in a GIF)
            player = self.universe.get_active_map().get_entity_by_name("player1")

            # We'd better validate...
            if (player):

                # Colorify!
                player.colorify(self.custom_avatar_data)
            """


        if ( "draw-all-maps" in options ):
            self.draw_all_maps = ( int( options["draw-all-maps"] ) == 1 )

        if ( "render-background" in options ):
            self.render_background = ( int( options["render-background"] ) == 1 )

        if ( "align" in options ):
            self.align = options["align"]


        """
        # Now get any upgrade...
        upgrade_collection = xml.get_nodes_by_tag("upgrade")

        for ref_upgrade in upgrade_collection:

            #self.upgrades.append( PauseMenuSkillPanelOptionUpgrade(session, ref_upgrade) )
            pass
        """


        # For chaining
        return self


    def setup_text_blasters(self, current_version):

        for upgrade in self.upgrades:

            # We want the next possible upgrade
            if (upgrade.version == (current_version + 1)):

                w = int(PAUSE_MENU_CONTENT_WIDTH / 2)
                padding = 10

                blasters = {
                    "upgrade-title": TextBlaster("Next:  %s" % upgrade.title, fade_speed = 1.0, max_width = w - (padding * 2), align = "right"),
                    "upgrade-required-level": TextBlaster("Required Level:  %d" % upgrade.required_level, fade_speed = 1.0, max_width = w - (padding * 2), align = "right"),
                    "upgrade-description": TextBlaster(upgrade.description, fade_speed = 1.0, delay_max = 1, max_width = w - (padding * 2)),
                    "upgrade-action-text": TextBlaster(upgrade.action_text, fade_speed = 1.0, max_width = w - (padding * 2), align = "center")
                }

                return blasters


                #blaster = TextBlaster("This is a simple textified blaster x test...", fade_speed = 0.25, max_width = 75, align = "right")

        # I guess we couldn't find anything...
        return None


    # Straight-up GIF height
    def report_widget_height(self, text_renderer):

        return self.get_height(text_renderer)


    def pre_process(self):

        if (self.universe):

            self.universe.session = self.universe.create_dummy_session()

            """
            m = self.universe.get_active_map()

            if (m):

                player = m.get_entity_by_name("player1")

                if (player):

                    self.universe.get_camera().center_on_entity_within_map(player, m)
                    self.universe.get_camera().zap()

                    log2( "cam x = ", self.universe.get_camera().x )
            """


    # Begin playback on this gif from the beginning
    def begin_playback(self, map_name, replay_data_path):

        # Make sure the universe appreciates that this is the active map, worth processing and everything
        self.universe.set_active_map_by_name( map_name )


        # Ensure that the active map in this preview is set to type "gif" to prevent autosaves, etc.
        self.universe.get_active_map().set_type("gif")


        # Disable any player entity not named "player1."  **Hack
        for player in self.universe.get_active_map().get_entities_by_type(GENUS_PLAYER):

            # Validate name
            if ( player.get_name() != "player1" ):

                # Disable within this preview
                player.set_status(STATUS_INACTIVE)

        # Make sure no enemy on the map hesitates
        for enemy in self.universe.get_active_map().get_entities_by_type(GENUS_ENEMY):

            # No hesitation
            enemy.no_hesitate()


        # Update replay data, if/a
        if (replay_data_path):

            # When we rebuild the map (for looping animations), we'll lose this replay data.
            # To recall the replay filepath, I'll save it as a param, then read that param just before ditching the map.
            self.universe.get_active_map().set_param(
                "replay-file",
                os.path.join(REPLAYS_PATH, replay_data_path)
            )

            # Initialize replay data
            self.universe.get_active_map().configure({
                "replay-file": os.path.join(REPLAYS_PATH, replay_data_path)
            })


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        #print "testing:  ", self
        #traceback.print_stack()

        self.debug_ccr = control_center
        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Check local event queue
        event = self.event_queue.fetch()

        # Handle all events until we've handled all of them...
        while (event):

            # Convenience
            (action, params) = (
                event.get_action(),
                event.get_params()
            )


            # Load universe?
            if (action == "load-universe"):

                # Set it up...
                self.universe = Universe(self.universe_name, MODE_GAME, control_center)

                # The GIF's universe should never pay attention to map memory files!
                self.universe.ignore_map_memory_files = True


                # Mark this universe as a gif
                self.universe.set_session_variable("core.is-gif", "1")


                # For GIFs, I'm going to emulate a "level 3" ability for each preview (?)
                for skill in SKILL_LIST:
                    self.universe.set_session_variable("core.skills.%s" % skill, "3")


                # Configure universe camera
                self.universe.get_camera().configure({
                    "width": self.get_width(),
                    "height": self.get_height( control_center.get_window_controller().get_default_text_controller().get_text_renderer() )
                })


                # Do preprocessing
                self.pre_process()

            # Set active map?
            elif (action == "activate-map"):

                # Do it...
                self.universe.activate_map_on_layer_by_name(
                    params["name"],
                    LAYER_FOREGROUND,
                    control_center = control_center
                )
                #log2( "activate map:  %s" % event.get_param("name") )

                # Get the active map
                m = self.universe.get_active_map()

                # Validate
                if (m):

                    # Make sure to mark the map as type "gif" to prevent autosave, etc.
                    m.set_type("gif")


                    # Disable any player entity not named "player1."  **Hack
                    for player in m.get_entities_by_type(GENUS_PLAYER):

                        # Validate name
                        if ( player.get_name() != "player1" ):

                            # Disable within this preview
                            player.set_status(STATUS_INACTIVE)

            # Load replay file?
            elif ( action == "load-replay-file" ):

                # When we rebuild the map (for looping animations), we'll lose this replay data.
                # To recall the replay filepath, I'll save it as a param, then read that param just before ditching the map.
                self.universe.get_active_map().set_param(
                    "replay-file",
                    os.path.join(REPLAYS_PATH, params["replay-file"])
                )

                # Initialize replay data
                self.universe.get_active_map().configure({
                    "replay-file": os.path.join(REPLAYS_PATH, params["replay-file"])
                })

            # Set the GIF "player's" active skill?
            elif ( action == "set-active-skill" ):

                # Set skill, hard-coding it to a level 3 skill
                self.universe.get_session_variable("core.skills.%s" % params["active-skill"]).set_value("3")
                self.universe.get_session_variable("core.player1.skill1").set_value(params["active-skill"])

            # Customize the avatar on the map
            elif (action == "customize-avatar"):

                # Find the player (always player1 in a GIF)
                player = self.universe.get_active_map().get_entity_by_name("player1")

                # We'd better validate...
                if (player):

                    # Colorify!
                    player.colorify(
                        params["avatar-data"]
                    )


            # Loop until done
            event = self.event_queue.fetch()


        # Process universe, if/a
        if (self.universe):

            # Fetch input controller
            input_controller = control_center.get_input_controller()


            # Lock all input (we don't want the player's key movements affecting the GIFs!)
            input_controller.lock_all_input()

            self.universe.get_camera().lock()
            # Process universe game logic
            self.universe.process_game_logic(control_center)
            self.universe.get_camera().unlock()

            # Unlock input
            input_controller.unlock_all_input()


            # Try to get the active map
            m = self.universe.get_active_map()

            # Validate
            if (m):

                player = m.get_entity_by_name("player1")

                if (0 and player):

                    self.universe.get_camera().center_on_entity_within_map(player, m)
                    self.universe.get_camera().zap()



                # Process map replay data using this GIF's Universe object
                m.process_replay_data(control_center, self.universe)


                # Check map for reload flag
                if (m.requires_reload):

                    # Before disposing of the Map object, let's recall the path to the replay data
                    replay_data_path = m.get_param("replay-file")

                    # Remember map name for a moment
                    name = self.universe.remove_map_on_layer_by_name( m.name, LAYER_FOREGROUND ).name # .remove_... returns the removed map, we'll borrow its name


                    # Immediately send a fresh build map request, thus "reloading" the map
                    self.universe.build_map_on_layer_by_name(name, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center)

                    # Activate the map
                    self.universe.activate_map_on_layer_by_name(name, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center)


                    # Get the active map
                    m = self.universe.get_active_map()

                    # Validate
                    if (m):

                        # Make sure to mark the map as type "gif" to prevent autosave, etc.
                        m.set_type("gif")


                    # Did the active map have a replay filepath?
                    if (replay_data_path):

                        # We also must again set the param for continuous looping
                        self.universe.get_active_map().set_param(
                            "replay-file",
                            replay_data_path
                        )

                        # Initialize replay data on the rebuilt Map object
                        self.universe.get_active_map().configure({
                            "replay-file": replay_data_path
                        })


                    # Reset all skill timers
                    for skill in ACTIVE_SKILL_LIST:

                        # The GIF shouldn't adhere to recharge times across map reloads
                        self.universe.get_session_variable("core.skills.%s:recharge-remaining" % skill).set_value("0")


                    """
                    # Custom avatar?
                    if (self.custom_avatar_data):

                        # Find the player (always player1 in a GIF)
                        player = self.map.get_entity_by_name("player1")

                        # We'd better validate...
                        if (player):

                            # Colorify!
                            player.colorify(self.custom_avatar_data)


                    self.pre_process()
                    """


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions each preview map's viewport gets...
        (width, height) = (
            self.get_width(),
            self.get_height(text_renderer)
        )

        # Define area for preview maps
        rPreview = (rx, ry, width, height)


        # Alignment adjustments
        if (self.align == "center"):

            rPreview = offset_rect(rPreview, -1 * int(width / 2), 0)

        elif (self.align == "right"):

            rPreview = offset_rect(rPreview, -width, 0)


        # Use our own widget alpha value
        alpha = self.alpha_controller.get_interval()


        # Confine rendering to the size of this GIF
        window_controller.get_scissor_controller().push(rPreview)

        # Fresh background for whatever we happen to draw, if requested
        if (self.render_background):

            # hard-coded color
            window_controller.get_geometry_controller().draw_rect(rPreview[0], rPreview[1], rPreview[2], rPreview[3], (25, 25, 25, alpha))


        # Validate dedicated GIF universe
        if (self.universe):

            # Hacked in check for custom universe tilesheet.
            # The universe handles this on its own in draw_game, but gifs use the lower-level draw_map calls directly; thus, we must do this hack.
            if (self.universe.custom_tilesheet):

                # Overwrite the default tilesheet param
                tilesheet_sprite = self.universe.custom_tilesheet


            # Grab a reference to the active map; we might only draw it, or we might draw all of the (on-screen) maps
            active_map = self.universe.get_active_map()

            # Loop all maps
            for name in self.universe.visible_maps[LAYER_FOREGROUND]:

                # Convenience
                m = self.universe.visible_maps[LAYER_FOREGROUND][name]

                # If we're drawing all maps, then we'll check universe camera data...
                if (self.draw_all_maps):

                    # Calculate the map's universal coordinates
                    (ux, uy) = (
                        m.x * TILE_WIDTH,
                        m.y * TILE_HEIGHT
                    )
                    logn( "gif", "testing:  ", (ux, uy) )

                    # Calculate where we will render this map
                    rAdjusted = offset_rect(
                        rPreview,
                        x = ux - self.universe.get_camera().x,#-int( ( (m.width * TILE_WIDTH) - rPreview[2] ) / 2),
                        y = uy - self.universe.get_camera().y#-int( ( (m.height * TILE_HEIGHT) - rPreview[3] ) / 2)
                    )
                    logn( "gif", "testing:  ", rAdjusted )


                    # Render the map
                    self.universe.draw_map_on_layer_with_explicit_offset(m.name, LAYER_FOREGROUND, rAdjusted[0], rAdjusted[1], tilesheet_sprite, additional_sprites, MODE_GAME, control_center = self.debug_ccr, scale = 1.0, gl_color = (1, 1, 1, alpha))
                    #self.universe.draw_map_on_layer_with_explicit_offset(m.name, LAYER_FOREGROUND, 0, 0, tilesheet_sprite, additional_sprites, MODE_GAME, control_center = self.debug_ccr, scale = 1.0, gl_color = (1, 1, 1, alpha))

                # If we're not in "draw all maps" mode, then we must confirm that this is the active map.
                elif (m == active_map):

                    # Calculate the map's universal coordinates
                    (ux, uy) = (
                        m.x * TILE_WIDTH,
                        m.y * TILE_HEIGHT
                    )


                    # Get player entity.  We're going to manually calculate centering logic for single-map GIFs,
                    # because they're not playing nicely with the .focus() method.
                    player = m.get_entity_by_name("player1")

                    # Validate
                    if (player):

                        # Center camera on player
                        self.universe.get_camera().configure({
                            "target-x": ( ux + player.get_x() - int( self.universe.get_camera().get_width() / 2 ) ),
                            "target-y": ( uy + player.get_y() - int( self.universe.get_camera().get_height() / 2 ) )
                        })

                        # Zap camera
                        self.universe.get_camera().zap()


                    # Calculate where we will render this map
                    rAdjusted = offset_rect(
                        rPreview,
                        x = ux - self.universe.get_camera().x,#-int( ( (m.width * TILE_WIDTH) - rPreview[2] ) / 2),
                        y = uy - self.universe.get_camera().y#-int( ( (m.height * TILE_HEIGHT) - rPreview[3] ) / 2)
                    )


                    # Render the map
                    self.universe.draw_map_on_layer_with_explicit_offset(m.name, LAYER_FOREGROUND, rAdjusted[0], rAdjusted[1], tilesheet_sprite, additional_sprites, MODE_GAME, control_center = self.debug_ccr, scale = 1.0, gl_color = (1, 1, 1, alpha))


        # Frame the entire GIF (?)
        window_controller.get_geometry_controller().draw_rect_frame(rPreview[0], rPreview[1], rPreview[2], rPreview[3], (0, 0, 0, alpha), 2)

        # Disable that scissor test we called for; we're done rendering!
        window_controller.get_scissor_controller().pop()


class Worldmap(UIWidget):

    def __init__(self):#, width, height, session):

        UIWidget.__init__(self, selector = "map")


        # We'll want to remember which map is active
        self.active_map_name = ""

        # Track worldmap data (just steal it from the universe basically)
        self.map_data = None


        # Track which kind of map we're using
        self.view = "gold"

        # Also track what kind of focus, if any, we have on the map widget
        self.input_mode = "" # pan, zoom, bookmark, ?


        # When in travel input mode, we want to know which map (town) we have selected at the moment.
        self.selected_map_name = "town2.level2"#"Edenton"


        # Alignment
        self.align = "left" # left, center, right        


        # Keep a queue of events
        self.event_queue = EventQueue()


        # Track current zoom level
        self.scale_controller = IntervalController(
            interval = 0.75,
            target = 0.75,
            speed_in = 0.01,
            speed_out = 0.01
        )


        # Pan controllers
        self.hpan_controller = IntervalController(
            interval = 0,
            target = 0,
            speed_in = 3,
            speed_out = 3,
            integer_based = True
        )

        self.vpan_controller = IntervalController(
            interval = 0,
            target = 0,
            speed_in = 3,
            speed_out = 3,
            integer_based = True
        )

        # I also want to configure custom accelerators for both pan controllers
        for o in (self.hpan_controller, self.vpan_controller):

            # The greater the distance, the faster it pans to catch up
            o.configure({
                "accelerator": lambda x, dy, c = o: min( 40, max( x, int( abs( c.get_interval() - c.get_target() ) / 20) ) ) # Use max() to ensure we always move at least as fast as the default speed (and we definitely never want a speed of 0!), then make sure it never exceeds 40 (hard-coded)
            })


        # Fire build event to gather all map data
        self.event_queue.add(
            action = "build"
        )


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "align" in options ):
            self.align = options["align"]

        if ( "input-mode" in options ):
            self.input_mode = options["input-mode"]

        #if ( "

        if ( "zoom" in options ):

            self.scale_controller.set_interval(
                float( options["zoom"] )
            )

            self.scale_controller.set_target(
                float( options["zoom"] )
            )

        if ( "view" in options ):
            self.view = options["view"]

        # Which town should the cursor highlight?
        if ( "selected-map" in options ):
            self.selected_map_name = options["selected-map"]


        # For chaining
        return self


    # Simple worldmap height
    def report_widget_height(self, text_renderer):

        return self.get_height(text_renderer)


    def zoom(self, amount = 0):

        # Adjust scale
        self.scale_controller.set_target(
            self.scale_controller.get_interval() + amount
        )


    # Center on a given worldmap location
    def center_on_map_by_name(self, name, with_effects = True):

        # Compute maximum reach of the worldmap, counting only overworld maps
        (worldmap_maxX, worldmap_maxY) = (
            (max(self.map_data[m].x for m in self.map_data if self.map_data[m].has_class("overworld")) - min(self.map_data[m].x for m in self.map_data if self.map_data[m].has_class("overworld"))),
            (max(self.map_data[m].y for m in self.map_data if self.map_data[m].has_class("overworld")) - min(self.map_data[m].y for m in self.map_data if self.map_data[m].has_class("overworld")))
        )

        # Determine farthest west/north maps in the overworld
        (worldmap_minX, worldmap_minY) = (
            min(self.map_data[m].x for m in self.map_data if self.map_data[m].has_class("overworld")),
            min(self.map_data[m].y for m in self.map_data if self.map_data[m].has_class("overworld"))
        )


        # Overworld dimensions, in tile units
        (worldmap_width, worldmap_height) = (
            worldmap_maxX - worldmap_minX,
            worldmap_maxY - worldmap_minY
        )


        (gw, gh) = (1, 1)

        # Render scale
        scale = self.scale_controller.get_interval()


        # Where would we ordinarily render the given map on the worldmap?
        (x, y, w, h) = (
            int( ( (self.map_data[name].x - worldmap_minX) - int(worldmap_width / 2) ) * scale ),
            int( ( (self.map_data[name].y - worldmap_minY) - int(worldmap_height / 2) ) * scale ),
            int( (self.map_data[name].width * gw * scale) ),
            int( (self.map_data[name].height * gh * scale) )
        )


        # Update hpan and vpan controllers to center on that default location
        self.hpan_controller.set_target(x)
        self.vpan_controller.set_target(y)


        # Include visual flair?
        if (with_effects):

            # Let's add a little "zoom in" effect, just for show
            self.scale_controller.set_interval(
                self.scale_controller.get_interval() - 0.5
            )


    def handle_user_input(self, control_center, universe):

        # Events that result from processing the worldmap
        results = EventQueue()


        # Pan?
        if (self.input_mode == "pan"):

            # Fetch the input controller's gameplay input
            user_input = control_center.get_input_controller().get_gameplay_input()

            # Fetch touched keys to use as raw keyboard input
            touched_keys = control_center.get_input_controller().get_touched_keys()


            # Hitting ESC or "enter" cancels the pan
            if ( (K_ESCAPE in touched_keys) or (INPUT_SELECTION_ACTIVATE in user_input) ):

                # No input mode
                self.input_mode = ""

                results.add(
                    action = "commit:game.worldmap.yield"
                )

            else:

                # Pan left
                if (INPUT_MOVE_LEFT in user_input):

                    # Update the interval itself, don't animate
                    self.hpan_controller.set_interval(
                        self.hpan_controller.get_interval() - 2
                    )

                    # Set target equal to current interval
                    self.hpan_controller.set_target(
                        self.hpan_controller.get_interval()
                    )

                if (INPUT_MOVE_RIGHT in user_input):

                    # Update the interval itself, don't animate
                    self.hpan_controller.set_interval(
                        self.hpan_controller.get_interval() + 2
                    )

                    # Set target equal to current interval
                    self.hpan_controller.set_target(
                        self.hpan_controller.get_interval()
                    )

                if (INPUT_MOVE_UP in user_input):

                    # Update the interval itself, don't animate
                    self.vpan_controller.set_interval(
                        self.vpan_controller.get_interval() - 2
                    )

                    # Set target equal to current interval
                    self.vpan_controller.set_target(
                        self.vpan_controller.get_interval()
                    )

                if (INPUT_MOVE_DOWN in user_input):

                    # Update the interval itself, don't animate
                    self.vpan_controller.set_interval(
                        self.vpan_controller.get_interval() + 2
                    )

                    # Set target equal to current interval
                    self.vpan_controller.set_target(
                        self.vpan_controller.get_interval()
                    )

        # Zoom
        elif (self.input_mode == "zoom"):

            # Fetch the input controller's gameplay input
            user_input = control_center.get_input_controller().get_gameplay_input()

            # Fetch touched keys to use as raw keyboard input
            touched_keys = control_center.get_input_controller().get_touched_keys()


            # Hitting ESC or "enter" cancels the zoom
            if ( (K_ESCAPE in touched_keys) or (INPUT_SELECTION_ACTIVATE in user_input) ):

                # No input mode
                self.input_mode = ""

                results.add(
                    action = "commit:game.worldmap.yield"
                )

            else:

                # Zoom in
                if (INPUT_MOVE_UP in user_input):

                    # Zoom in 25%
                    self.zoom(0.25)

                    # Track zoom setting via session
                    universe.set_session_variable( "core.worldmap.zoom", "%s" % self.scale_controller.get_target() )

                # Zoom out
                elif (INPUT_MOVE_DOWN in user_input):

                    # Zoom out 25%
                    self.zoom(-0.25)

                    # Track zoom setting via session
                    universe.set_session_variable( "core.worldmap.zoom", "%s" % self.scale_controller.get_target() )


        # Travel
        elif (self.input_mode == "travel"):

            # Fetch the input controller's gameplay input
            user_input = control_center.get_input_controller().get_gameplay_input()

            # Fetch touched keys to use as raw keyboard input
            touched_keys = control_center.get_input_controller().get_touched_keys()


            # Hitting ESC cancels travel navigation
            if ( (K_ESCAPE in touched_keys) ):#or (INPUT_SELECTION_ACTIVATE in user_input) ):

                # No input mode
                self.input_mode = ""

                results.add(
                    action = "commit:game.worldmap.yield"
                )

            else:

                if (INPUT_SELECTION_PAGEDOWN in user_input):
                    self.selected_map_name = "town2.level2"

                elif (INPUT_SELECTION_LEFT in user_input):

                    # Get currently selected map data
                    map_data = universe.get_map_data(self.selected_map_name)

                    # Validate
                    if (map_data):

                        # Track potential cursor input matches
                        matches = []

                        # Now let's loop all other town capitals (i.e. travel destinations)
                        for capital_data in universe.get_map_data_by_class("capital"):

                            # We can only fast travel to locations we've previously at least neared
                            if ( capital_data.is_map_visible() ):

                                # Pressing left means we definitely want a map west of the current map
                                if (capital_data.x < map_data.x):

                                    # Calculate the angle between the current map and the iterated capital
                                    angle = math.degrees( math.atan( float( abs(map_data.y - capital_data.y) ) / float( abs(map_data.x - capital_data.x) ) ) )

                                    # Add it as a potential match
                                    matches.append({
                                        "map": capital_data.get_name(),
                                        "title": capital_data.get_title(),
                                        "deviation": int(angle / 45),
                                        "angle": angle,
                                        "dx": abs(map_data.x - capital_data.x),
                                        "dy": abs(map_data.y - capital_data.y)
                                    })

                        # Sort matches by rank.  In this case, lower rank is better (i.e. closer)
                        matches = sorted(
                            matches,
                            key = lambda o: o["angle"] * ( math.pow(o["dx"], 2) + math.pow(o["dy"], 2) )
                        )

                        # Did we find a result?
                        if ( len(matches) > 0 ):

                            # Track the newly-selected map name
                            self.selected_map_name = matches[0]["map"]

                            # Move to the selected map
                            #self.hpan_controller.set_target
                            self.center_on_map_by_name(self.selected_map_name, with_effects = False)

                elif (INPUT_SELECTION_RIGHT in user_input):

                    # Get currently selected map data
                    map_data = universe.get_map_data(self.selected_map_name)

                    # Validate
                    if (map_data):

                        # Track potential cursor input matches
                        matches = []

                        # Now let's loop all other town capitals (i.e. travel destinations)
                        for capital_data in universe.get_map_data_by_class("capital"):

                            # We can only fast travel to locations we've previously at least neared
                            if ( capital_data.is_map_visible() ):

                                # Pressing right means we definitely want a map east of the current map
                                if (capital_data.x > map_data.x):

                                    # Calculate the angle between the current map and the iterated capital
                                    angle = math.degrees( math.atan( float( abs(map_data.y - capital_data.y) ) / float( abs(map_data.x - capital_data.x) ) ) )

                                    # Add it as a potential match
                                    matches.append({
                                        "map": capital_data.get_name(),
                                        "title": capital_data.get_title(),
                                        "deviation": int(angle / 45),
                                        "angle": angle,
                                        "dx": abs(map_data.x - capital_data.x),
                                        "dy": abs(map_data.y - capital_data.y)
                                    })

                        # Sort matches by rank.  In this case, lower rank is better (i.e. closer)
                        matches = sorted(
                            matches,
                            key = lambda o: o["angle"] * ( math.pow(o["dx"], 2) + math.pow(o["dy"], 2) )
                        )

                        # Did we find a result?
                        if ( len(matches) > 0 ):

                            # Track the newly-selected map name
                            self.selected_map_name = matches[0]["map"]

                            # Move to the selected map
                            #self.hpan_controller.set_target
                            self.center_on_map_by_name(self.selected_map_name, with_effects = False)

                elif (INPUT_SELECTION_UP in user_input):

                    # Get currently selected map data
                    map_data = universe.get_map_data(self.selected_map_name)

                    # Validate
                    if (map_data):

                        # Track potential cursor input matches
                        matches = []

                        # Now let's loop all other town capitals (i.e. travel destinations)
                        for capital_data in universe.get_map_data_by_class("capital"):

                            # We can only fast travel to locations we've previously at least neared
                            if ( capital_data.is_map_visible() ):

                                # Pressing up means we definitely want a map north of the current map
                                if (capital_data.y < map_data.y):

                                    # Calculate the angle between the current map and the iterated capital
                                    angle = math.degrees( math.atan( float( abs(map_data.x - capital_data.x) ) / float( abs(map_data.y - capital_data.y) ) ) )

                                    # Add it as a potential match
                                    matches.append({
                                        "map": capital_data.get_name(),
                                        "title": capital_data.get_title(),
                                        "deviation": int(angle / 45),
                                        "angle": angle,
                                        "dx": abs(map_data.x - capital_data.x),
                                        "dy": abs(map_data.y - capital_data.y)
                                    })

                        # Sort matches by rank.  In this case, lower rank is better (i.e. closer)
                        matches = sorted(
                            matches,
                            key = lambda o: max( math.cos( math.radians( o["angle"] ) ), 0.75) * math.sqrt( math.pow(o["dx"], 2) + math.pow(o["dy"], 2) )
                        )

                        # Did we find a result?
                        if ( len(matches) > 0 ):

                            # Track the newly-selected map name
                            self.selected_map_name = matches[0]["map"]

                            # Move to the selected map
                            #self.hpan_controller.set_target
                            self.center_on_map_by_name(self.selected_map_name, with_effects = False)

                elif (INPUT_SELECTION_DOWN in user_input):

                    # Get currently selected map data
                    map_data = universe.get_map_data(self.selected_map_name)

                    # Validate
                    if (map_data):

                        # Track potential cursor input matches
                        matches = []

                        # Now let's loop all other town capitals (i.e. travel destinations)
                        for capital_data in universe.get_map_data_by_class("capital"):

                            # We can only fast travel to locations we've previously at least neared
                            if ( capital_data.is_map_visible() ):

                                # Pressing down means we definitely want a map south of the current map
                                if (capital_data.y > map_data.y):

                                    # Calculate the angle between the current map and the iterated capital
                                    angle = math.degrees( math.atan( float( abs(map_data.x - capital_data.x) ) / float( abs(map_data.y - capital_data.y) ) ) )

                                    # Add it as a potential match
                                    matches.append({
                                        "map": capital_data.get_name(),
                                        "title": capital_data.get_title(),
                                        "deviation": int(angle / 45),
                                        "angle": angle,
                                        "dx": abs(map_data.x - capital_data.x),
                                        "dy": abs(map_data.y - capital_data.y)
                                    })

                        # Sort matches by rank.  In this case, lower rank is better (i.e. closer)
                        matches = sorted(
                            matches,
                            key = lambda o: max( math.cos( math.radians( o["angle"] ) ), 0.75) * math.sqrt( math.pow(o["dx"], 2) + math.pow(o["dy"], 2) )
                        )

                        # Did we find a result?
                        if ( len(matches) > 0 ):

                            # Track the newly-selected map name
                            self.selected_map_name = matches[0]["map"]

                            # Move to the selected map
                            #self.hpan_controller.set_target
                            self.center_on_map_by_name(self.selected_map_name, with_effects = False)

                # Selecting a town should raise a "show confirmation dialog" event.
                # The event's callback will query this widget for its data, so we don't need to provide it en-route.
                elif (INPUT_SELECTION_ACTIVATE in user_input):

                    results.add(
                        action = "show:game.worldmap.travel.confirm"
                    )


        # Return events
        return results


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Before beginning:  Each town can have more than one level, but we select one single level to serve
        #    as the town's "capital."  If our selected map is not a capital, let's try to find the nearby capital.
        data = universe.get_map_data(self.selected_map_name)

        # Validate
        if (data):

            # Not a capital?
            if ( not data.has_class("capital") ):

                # Loop through all capital maps, trying to find one with the same name (same town)
                for data2 in universe.get_map_data_by_class("capital"):

                    # Found the capital in the same townN?
                    if ( data2.get_title() == data.get_title() ):

                        # Update worldmap travel selection to use the town's capital
                        self.configure({
                            "selected-map": data2.get_name()
                        })
                        log2(
                            "Debug:  Updating worldmap selected town from '%s' to '%s'" % ( data.get_name(), data2.get_name() )
                        )


        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Process horizontal panning
        results.append(
            self.hpan_controller.process()
        )

        # Process vertical panning
        results.append(
            self.vpan_controller.process()
        )


        # Process scaling
        results.append(
            self.scale_controller.process()
        )


        # Process events
        event = self.event_queue.fetch()

        # All of them
        while (event):

            # Build?
            if ( event.get_action() == "build" ):

                # Fetch the active map's name
                self.active_map_name = universe.get_active_map().name

                # Just grab a reference to the universe's foreground layermap data.  We're not going to change it or anything,
                # and we don't care at all about the background (parallax) layer.
                self.map_data = universe.map_data[LAYER_FOREGROUND]


                # Center on the active map when we first display the Worldmap widget
                self.center_on_map_by_name(self.active_map_name)


            # Loop
            event = self.event_queue.fetch()


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Worldmap widget imensions
        (width, height) = (
            self.get_width(),
            self.get_height(text_renderer)
        )


        # Align center?
        if (self.align == "center"):

            rx -= int(width / 2)

        # Align right?
        elif (self.align == "right"):

            rx -= width


        # Use our own widget alpha value
        alpha = self.alpha_controller.get_interval()

        # Render scale
        scale = self.scale_controller.get_interval()


        # Compute maximum reach of the worldmap, counting only overworld maps
        (worldmap_maxX, worldmap_maxY) = (
            (max(self.map_data[m].x for m in self.map_data if self.map_data[m].has_class("overworld")) - min(self.map_data[m].x for m in self.map_data if self.map_data[m].has_class("overworld"))),
            (max(self.map_data[m].y for m in self.map_data if self.map_data[m].has_class("overworld")) - min(self.map_data[m].y for m in self.map_data if self.map_data[m].has_class("overworld")))
        )

        # Determine farthest west/north maps in the overworld
        (worldmap_minX, worldmap_minY) = (
            min(self.map_data[m].x for m in self.map_data if self.map_data[m].has_class("overworld")),
            min(self.map_data[m].y for m in self.map_data if self.map_data[m].has_class("overworld"))
        )


        # Overworld dimensions, in tile units
        (worldmap_width, worldmap_height) = (
            worldmap_maxX - worldmap_minX,
            worldmap_maxY - worldmap_minY
        )


        (ux, uy) = (
            self.map_data[self.active_map_name].x,
            self.map_data[self.active_map_name].y
        )


        (gw, gh) = (1, 1)


        (cx, cy) = (
            rx + int(width / 2),
            ry + int(height / 2)
        )


        (relX, relY) = (
            (cx + ux),
            (cy + uy)
        )

        # Scissor on the worldmap drawable region
        window_controller.get_scissor_controller().push( (rx, ry, width, height) )


        # Loop all maps
        for m in self.map_data:#self.get_visible_map_names():

            # Only render visible maps, and only render overworld maps
            if ( ( self.map_data[m].is_map_visible() ) and ( self.map_data[m].has_class("overworld") ) ):

                # Calculate render position
                (x, y, w, h) = (
                    cx + int( ( (self.map_data[m].x - worldmap_minX) - int(worldmap_width / 2) ) * scale ),
                    cy + int( ( (self.map_data[m].y - worldmap_minY) - int(worldmap_height / 2) ) * scale ),
                    int( (self.map_data[m].width * gw * scale) ),
                    int( (self.map_data[m].height * gh * scale) )
                )

                frame_size = max(1, int(scale))


                # What color should we use for this cell?  We'll start by assuming a dim "seen but not visited" color...
                color = (115, 115, 115)


                # Are we looking at the "uncollected gold" view?
                if (self.view == "gold"):

                    # But if we've visited it...
                    if (self.map_data[m].visited):

                        # Does it have any gold left?  If so, it's a strong plain white:  visited, but not finished...
                        if (self.map_data[m].gold_remaining > 0):

                            color = (225, 225, 225)

                        # No gold left indicates a completed map; we'll render it in a celebratory gold color...
                        else:

                            color = (219, 183, 21)


                    # Lastly, always overwrite the color for the current map...
                    if (m == self.active_map_name):

                        color = (25, 225, 25)

                # Are we looking at the "unfinished puzzle/challenge rooms" view?
                elif ( self.view in ("puzzle", "challenge") ):

                    # Does this map contain a link to a puzzle/challenge?
                    if ( self.map_data[m].has_class("%s-door" % self.view) ):

                        # Check complete status on this level's associated puzzle level
                        if ( self.map_data[ self.map_data[m].get_rel() ].is_map_completed() ):

                            # Render in celebratory gold!
                            color = (219, 183, 21)

                        # Render incomplete puzzle linking maps in... red???
                        else:

                            color = (225, 25, 25)

                    # Nope...
                    else:

                        # If we've visited it, at least give it a strong white color
                        if (self.map_data[m].visited):

                            # Gold count doesn't matter in this view...
                            color = (225, 225, 225)

                        # Stay with the default dim grey color
                        else:
                            pass


                    # Lastly, always overwrite the color for the current map...
                    if (m == self.active_map_name):

                        # .... ?
                        color = (25, 225, 25)


                # Define final rect
                r = (x, y, w, h)

                # Offset by current pan amount
                r = offset_rect(
                    r,
                    x = -self.hpan_controller.get_interval(),
                    y = -self.vpan_controller.get_interval()
                )


                window_controller.get_geometry_controller().draw_rect(r[0], r[1], r[2], r[3], set_alpha_for_rgb(alpha, (0, 0, 0)))
                window_controller.get_geometry_controller().draw_rect(r[0] + frame_size, r[1] + frame_size, r[2] - (2 * frame_size), r[3] - (2 * frame_size), set_alpha_for_rgb(alpha, (100, 100, 100)))
                window_controller.get_geometry_controller().draw_rect(r[0] + (2 * frame_size), r[1] + (2 * frame_size), r[2] - (4 * frame_size), r[3] - (4 * frame_size), set_alpha_for_rgb(alpha, color))


        # Make a second rendering pass, this time rendering town capital names (if we've visited the area)
        # Loop all maps
        for m in self.map_data:#self.get_visible_map_names():

            # Only render visible town maps, and only render overworld maps
            if ( ( self.map_data[m].is_map_visible() ) and ( self.map_data[m].has_class("town") ) and ( self.map_data[m].has_class("capital") ) ):

                # Calculate render position
                (x, y, w, h) = (
                    cx + int( ( (self.map_data[m].x - worldmap_minX) - int(worldmap_width / 2) ) * scale ),
                    cy + int( ( (self.map_data[m].y - worldmap_minY) - int(worldmap_height / 2) ) * scale ),
                    int( (self.map_data[m].width * gw * scale) ),
                    int( (self.map_data[m].height * gh * scale) )
                )

                # Define final rect
                r = (x, y, w, h)

                # Offset by current pan amount
                r = offset_rect(
                    r,
                    x = -self.hpan_controller.get_interval(),
                    y = -self.vpan_controller.get_interval()
                )


                # In "travel" mode, we want to highlight the currently selected map name
                if (self.input_mode == "travel"):

                    # Highlight the selected map's text string
                    if ( self.map_data[m].get_name() == self.selected_map_name ):

                        # Render just above the grid with some opacity
                        text_renderer.render_with_wrap( self.map_data[m].get_title(), r[0] + int(r[2] / 2), r[1] - text_renderer.font_height, set_alpha_for_rgb(alpha * 0.75, (207, 106, 19)), align = "center")

                    # Render all other town names in a subdued font
                    else:

                        # Render just above the grid with some opacity
                        text_renderer.render_with_wrap( self.map_data[m].get_title(), r[0] + int(r[2] / 2), r[1] - text_renderer.font_height, set_alpha_for_rgb(alpha * 0.75, (225, 225, 225)), align = "center")

                # In all other modes, we render the town names in the same color
                else:

                    # Render just above the grid with some opacity
                    text_renderer.render_with_wrap( self.map_data[m].get_title(), r[0] + int(r[2] / 2), r[1] - text_renderer.font_height, set_alpha_for_rgb(alpha * 0.75, (207, 106, 19)), align = "center")

                #window_controller.get_geometry_controller().draw_rect(r[0], r[1], r[2], r[3], set_alpha_for_rgb(alpha, (0, 0, 0)))
                #window_controller.get_geometry_controller().draw_rect(r[0] + frame_size, r[1] + frame_size, r[2] - (2 * frame_size), r[3] - (2 * frame_size), set_alpha_for_rgb(alpha, (100, 100, 100)))
                #window_controller.get_geometry_controller().draw_rect(r[0] + (2 * frame_size), r[1] + (2 * frame_size), r[2] - (4 * frame_size), r[3] - (4 * frame_size), set_alpha_for_rgb(alpha, color))


        # Special label for pan mode
        if (self.input_mode == "pan"):

            # Backdrop
            window_controller.get_geometry_controller().draw_rect(rx, ry + height - text_renderer.font_height - 10, width, text_renderer.font_height + 10, set_alpha_for_rgb( 0.75 * alpha, (0, 0, 0) ))

            # Define lines
            lines = (
                "Pan Mode:",
                "Movement keys pan the map",
                "Press ESC to exit"
            )

            # Message
            for y in range( 0, len(lines) ):

                # Align bottom, calculate necessary offset
                offset = len(lines) - y - 1

                # Render text
                text_renderer.render_with_wrap( lines[y], rx + 20, ry + height - text_renderer.font_height - 5 - (offset * text_renderer.font_height), self.get_color() )

        # Special label for zoom mode
        elif (self.input_mode == "zoom"):

            # Backdrop
            window_controller.get_geometry_controller().draw_rect(rx, ry + height - text_renderer.font_height - 10, width, text_renderer.font_height + 10, set_alpha_for_rgb( 0.5 * alpha, (0, 0, 0) ))

            # Define lines
            lines = (
                "Zoom Mode:",
                "Up/down keys adjust the zoom",
                "Press ESC to exit"
            )

            # Message
            for y in range( 0, len(lines) ):

                # Align bottom, calculate necessary offset
                offset = len(lines) - y - 1

                # Render text
                text_renderer.render_with_wrap( lines[y], rx + 20, ry + height - text_renderer.font_height - 5 - (offset * text_renderer.font_height), self.get_color() )

        # Special label for travel mode
        elif (self.input_mode == "travel"):

            # Backdrop
            window_controller.get_geometry_controller().draw_rect(rx, ry + height - text_renderer.font_height - 10, width, text_renderer.font_height + 10, set_alpha_for_rgb( 0.5 * alpha, (0, 0, 0) ))

            # Define lines
            lines = (
                "Travel Mode:",
                "Up/down/left/right keys to select a destination",
                "Press ESC to exit"
            )

            # Message
            for y in range( 0, len(lines) ):

                # Align bottom, calculate necessary offset
                offset = len(lines) - y - 1

                # Render text
                text_renderer.render_with_wrap( lines[y], rx + 20, ry + height - text_renderer.font_height - 5 - (offset * text_renderer.font_height), self.get_color() )


        # End this scissor test
        window_controller.get_scissor_controller().pop()
        #draw_rect(sx, sy, width, height, (225, 0, 0, 0.5))


class Graphic(UIWidget):

    def __init__(self):#, filename, width, height, holding_rect, node):

        UIWidget.__init__(self, selector = "graphic")


        # File path
        self.path = None#filename

        # Load the image as a spritesheet
        self.spritesheet = None


        # We'll place the graphic within a container
        self.holding_rect = (0, 0, 0, 0)

        # We may want to center within that container, or something...
        self.align = "left"

        # We might also want to control vertical alignment
        self.valign = "top"


        # Do we want to use lazy loading for this graphic?  (This means we don't actually load it until it appears on screen,
        # and potentially discard it after it scrolls offscreen.)
        self.lazy_loading = False

        # How long will we keep it around after it disappears?
        self.lazy_loading_discard_delay = 0


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Filename
        if ( "filename" in options ):

            # Validate path; discard path on fail...
            if ( not os.path.exists( options["filename"] ) ):

                # The path might be defined as folder-based.
                # If so, split by / and use os.path.join on the pieces.
                path = os.path.sep.join(
                    options["filename"].split("/")
                )

                # One more chance
                if ( os.path.exists(path) ):

                    # Use the new path
                    self.path = path

                # File not found
                else:
                    self.path = None

            # Cool
            else:
                self.path = options["filename"]


        # Width
        if ( "file-width" in options ):
            self.width = int( options["file-width"] )

        # Height
        if ( "file-height" in options ):
            self.height = int( options["file-height"] )


        # Do we have an explicit align setting?
        if ( "align" in options ):
            self.align = options["align"]

        # Explicit vertical alignment?
        if ( "valign" in options ):
            self.valign = options["valign"]


        # Use lazy loading?
        if ( "lazy-loading" in options ):
            self.lazy_loading = bool( options["lazy-loading"] )

        # What lazy loading discard delay might we have?
        if ( "lazy-loading-discard-delay" in options ):
            self.lazy_loading_discard_delay = int( options["lazy-loading-discard-delay"] )


        # About done; let's recalculate holding rect based on up-to-date graphic dimensions data
        self.holding_rect = ( 0, 0, self.width, self.height )#self.get_width(), self.get_height() )


        # For chaining
        return self


    def load_image(self):

        # Do we have a path to check?
        if (self.path):

            # Just in case...
            if (os.path.exists(self.path)):

                self.spritesheet = GLSpritesheet(self.path, self.width, self.height, first_pixel_transparent = False)

            else:
                logn( "image error", "Aborting:  %s does not exist!" % self.path )
                sys.exit()


    # If awake, we need to check for lazy loading
    def while_awake(self):

        # Base call
        UIWidget.while_awake(self)


        # If we're using lazy loading, we might need to load the image now
        if (self.lazy_loading):

            # Have we not yet loaded it?
            if (self.spritesheet == None):

                # Go ahead and load the image
                self.load_image()

                if ( self.spritesheet == None ):
                    log( "**Graphic NOT found '%s'" % self.path, self.spritesheet )
                    #print 5/0


            # Reset any discard delay tracking
            self.lazy_loading_discard_delay_interval = 0


    # If asleep and using lazy loading, we might be ready to ditch the image resource
    def while_asleep(self):

        # Base call
        UIWidget.while_asleep(self)


        # If we have lazy loading, then we'll discard the grahpic if it scrolls offscreen.
        # We don't necessarily do this immediately, though...
        if (self.lazy_loading):

            # Do we have a spritesheet to consider discarding?
            if (self.spritesheet != None):

                # Increment tracker
                self.lazy_loading_discard_delay_interval += 1

                # Time to discard image?
                if (self.lazy_loading_discard_delay_interval >= self.lazy_loading_discard_delay):

                    # Goodbye...
                    self.spritesheet = None

                    # Might as well reset this timer...
                    self.lazy_loading_discard_delay_interval = 0


    # Specified height for the image file
    def report_widget_height(self, text_renderer):

        return self.get_height(text_renderer)


    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Common widget post-processing
        self.__std_post_process__(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        if (self.spritesheet):

            #print "Graphic:  ", self.spritesheet

            # Default rendering point
            (rx, ry) = (
                sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
                sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
            )

            # Dimensions
            (width, height) = (
                self.get_width(),
                self.get_height(text_renderer)
            )

            # Align center?
            if (self.align == "center"):

                rx -= int(self.width / 2)

            # Align right?
            elif (self.align == "right"):

                rx -= self.width


            # Valign center?
            if (self.valign == "center"):

                # Center it
                ry -= int(height / 2)


            # Use our own widget alpha value
            alpha = self.alpha_controller.get_interval()


            #print "**graphic @ ", (rx, ry), alpha, (width, height)
            # Render...
            window_controller.get_gfx_controller().draw_sprite(rx, ry, width, height, self.spritesheet, frame = -1, gl_color = (1, 1, 1, alpha))

        else:

            #print "**Graphic missing, ", self.path

            # For graphics that don't use lazy loading, just make sure it's all set up.
            if (not self.lazy_loading):

                # If we haven't loaded yet...
                if (self.spritesheet == None):

                    # ... then we should (try to) load the image.
                    self.load_image()

