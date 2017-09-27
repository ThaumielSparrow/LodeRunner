from code.tools.eventqueue import EventQueue

from code.controllers.intervalcontroller import IntervalController

from code.utils.common import intersect, offset_rect, log, log2, xml_encode, xml_decode, set_alpha_for_rgb, rgb_to_glcolor, parse_rgb_from_string, evaluate_spatial_expression

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, LAYER_FOREGROUND, LAYER_BACKGROUND, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, CAMERA_SPEED, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_ACTIVATE, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, DATE_WIDTH, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, TILE_HEIGHT, PAD_AXIS, PAD_HAT, PAD_BUTTON, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT
from code.constants.common import INPUT_MOVE_UP, INPUT_MOVE_RIGHT, INPUT_MOVE_DOWN, INPUT_MOVE_LEFT, INPUT_SELECTION_ACTIVATE

from pygame.locals import K_ESCAPE, K_UP, K_DOWN 

# A generic widget object.
class Widget:

    def __init__(self, selector):

        # Track CSS selector name for this widget
        self.selector = selector

        # Optionally, a widget can have a namespace.  Must set after creation.
        self.namespace = None


        # A widget will keep a handle to its parent/owner.
        # (e.g. a Label within a Box widget)
        self.parent = None


        # CSS class (totally optional)
        self.css_class = ""

        # CSS state
        self.css_state = "" # no state, "active"


        # Parent (CSS) bloodline for this widget
        self.bloodline = "" # We can configure this via each widget's .configure() or .css() method


        # When a widget changes state (gets focus, loses focus, becomes active, etc.), we will
        # flag it as "dirty" so that it can update its CSS data as necessary
        self.dirty = True # Keep it dirty on spawn so that it can initially set up its CSS properties


        # We can mark a widget as "disabled."  Inheriting widgets often ignore this, but some
        # widgets -- GridMenus and RowMenus, for example -- use it for accurate cursor movement.
        self.disabled = False


        # A widget can define a "visibility" attribute.  Some widgets (perhaps subtitles) might only be visible with a parent (with-parent).
        self.visibility = "visible"

        # Widgets that only display when their parent is active will provide that parent's id
        self.parent_id = ""


        # A widget has a focus state.  Wdigets only react to input if they have focus (assuming they react at all)
        self.has_focus = False # Default to false

        # Sometimes a widget will indicate that it doesn't care about focus at all.
        self.uses_focus = True


        # At some points (mainly when refreshing overlays), we might want to lock the widget
        # to prevent various settings (e.g. slide controllers) from unwantedly changing during the repopulation process.
        self.lock_count = 0


        # A widget can store various "attributes" if it needs to.  Key listeners and such like to use these,
        # but any widget can use them for any purpose.
        self.attributes = {}


        # We will cache certain metrics
        self.cached_metrics = {}


        # Widget id
        self.id = ""

        # Widgets can have a rel attribute.  They can use it however they like (or not at all, typically)
        self.rel = ""


        # Coordinates
        self.x = 0
        self.y = 0


        # Dimensions
        self.width = "100%"
        self.height = 0

        # At any given time, a widget will have a maximum width/height region into which it can render.
        # Boxes within boxes may introduce padding that narrows the region available to the children.
        # These values may change over time.  We use these values to accurately compute
        # percentage-based positions / dimensions in real time.
        self.max_width = 0
        self.max_height = SCREEN_HEIGHT


        # We can also specify a minimum render height (useful for homogenizing the height of columns in a row, for instance)
        self.min_width = 0
        self.min_height = 0


        # Sometimes we want to force a certain style height onto a widget, sort of an absolute value
        self.style_width = 0
        self.style_height = 0


        # Display behavior (on focus only?  always?  etc...)
        self.display = "constant"

        # An absolute-positioned element won't factor into the overall width/height calculations of a cell element...
        self.position = "relative"


        # A widget can choose to render a border.  I leave it up to the individual widgets to react to this
        # flag in whichever fashion they prefer, if at all...
        self.render_border = False

        # A widget can also choose to fill in its background with its current gradient data
        self.fill = "" # active, always, or empty string

        # We can optionally specify that the widget should render as a title bar,
        # fitting properly within the rounded border.  Widgets must handle the
        # (somewhat hazy) logic of this within their own draw routine, though.
        self.uses_title_bar = False


        # Control widget alpha; default to "fade in" effect (interval 0, target 0.9)
        self.alpha_controller = IntervalController(
            interval = 0,
            target = 0.9,
            speed_in = 0.045,
            speed_out = 0.065
        )

        # A widget can also enable a simple lightbox effect.  The effect bases its value on the current
        # alpha value (like I said, simple...)  Each widget type is responsible for rendering the lightbox on its own terms.
        self.uses_lightbox = False


        # We can choose to slide widgets around if we want (e.g. transition effects in menus)
        self.hslide_controller = IntervalController(
            interval = 0,
            target = 0,
            speed_in = 20,
            speed_out = 20,
            integer_based = True # Rendering requires the use of integers; floats won't work
        )

        self.vslide_controller = IntervalController(
            interval = 0,
            target = 0,
            speed_in = 20,
            speed_out = 20,
            integer_based = True # Rendering requires the use of integers; floats won't work
        )


        """ Default style data.  Widgets can use some, all, or none of these. """
        # Background (rgb value)
        self.background_color = (0, 0, 0)

        # Gradient type (none, left-to-right, right-to-left, top-to-bottom, bottom-to-top)
        self.gradient = "none"

        # Gradient start / end (rgb values)
        self.gradient_start = (25, 25, 25)
        self.gradient_end = (225, 225, 225)

        # Background alpha factor
        self.background_alpha = 0.5

        # Rounded corners?
        self.rounded_corners = True

        # Text color
        self.color = (25, 125, 25)

        # Text alignment
        self.text_align = "left"

        # Border size (integer), color (rgb value)
        self.border_size = 0
        self.border_color = (25, 25, 225)

        # Border shadow size (integer), color (rgb value)
        self.shadow_size = 0
        self.shadow_color = (25, 25, 125)

        # BBCode (used chiefly by labels); hashed by color name
        self.bbcode = {}

        # Y-axis margins
        self.margin_top = 0
        self.margin_bottom = 0

        # Padding
        self.padding_top = 0
        self.padding_right = 0
        self.padding_bottom = 0
        self.padding_left = 0


    # Reset CSS data to defaults
    def __reset_css__(self):

        # Background (rgb value)
        self.background_color = (0, 0, 0)

        # Gradient type (none, left-to-right, right-to-left, top-to-bottom, bottom-to-top)
        self.gradient = "none"

        # Gradient start / end (rgb values)
        self.gradient_start = (25, 25, 25)
        self.gradient_end = (225, 225, 225)

        # Gradient alpha factor
        self.background_alpha = 0.5

        # Rounded corners?
        self.rounded_corners = True

        # Text color
        self.color = (25, 125, 25)

        # Text alignment
        self.text_align = "left"

        # Border size (integer), color (rgb value)
        self.border_size = 0
        self.border_color = (25, 25, 225)

        # Border shadow size (integer), color (rgb value)
        self.shadow_size = 0
        self.shadow_color = (25, 25, 125)

        # BBCode (used chiefly by labels); hashed by color name
        self.bbcode = {}

        # Y-axis margins
        self.margin_top = 0
        self.margin_bottom = 0

        # Padding
        self.padding_top = 0
        self.padding_right = 0
        self.padding_bottom = 0
        self.padding_left = 0


    # Configuration options for a generic widget
    def configure(self, options):

        # Invalidate all cached metrics, as position / dimension / etc. data may change here.
        self.invalidate_cached_metrics()


        # Widget id
        if ( "id" in options ):
            self.set_id( options["id"] )

        # Widget relation
        if ( "rel" in options ):
            self.rel = options["rel"]


        # Check for full bloodline
        if ( "bloodline" in options ):

            # Add this widget's selector type to the bloodline
            self.bloodline = "%s>%s" % ( options["bloodline"], "" )#self.get_selector() )

            #if ( options["bloodline"] == "rowmenu.inventory-directory:activerowmenu.inventory-directory:active" ):
            #    log( 5/0 )

            # In case this is the first in the bloodline, strip leading > (e.g. >rowmenu -> rowmenu)
            self.bloodline = self.bloodline.lstrip(">")


            # We need new CSS now, possibly
            self.dirty = True

        # CSS class configuration
        if ( "css-class" in options ):

            self.css_class = options["css-class"]

            # We need new CSS now, possibly
            self.dirty = True

        if ( "class" in options ):

            self.css_class = options["class"]

            # We need new CSS now, possibly
            self.dirty = True


        # Other standard things such as position, ID, etc...
        if ( "x" in options ):
            self.x = options["x"]

        if ( "y" in options ):
            self.y = options["y"]

        if ( "width" in options ):

            # Update width value
            self.width = options["width"]

            # Check for optional scale-width setting
            if ( "scale-width" in options ):

                # Scale
                try:
                    self.width = int( float( options["scale-width"] ) * int( self.width ) )
                except:
                    # Must be a percentage-based width, can't scale
                    self.width = options["width"]

            # Callback
            #self.on_resize()

        if ( "height" in options ):

            # Update height value
            self.height = options["height"]

            # Callback
            #self.on_resize()

        if ( "max-width" in options ):
            self.max_width = int( options["max-width"] )

        if ( "max-height" in options ):
            self.max_height = int( options["max-height"] )

        if ( "min-width" in options ):
            self.min_width = int( options["min-width"] )

        if ( "min-height" in options ):
            self.min_height = int( options["min-height"] )

        if ( "style-width" in options ):
            self.style_width = int( options["style-width"] )

        if ( "style-height" in options ):
            self.style_height = int( options["style-height"] )

        if ( "disabled" in options ):
            self.disabled = ( int( options["disabled"] ) == 1 )

        if ( "display" in options ):
            self.display = options["display"]

        if ( "visibility" in options ):
            self.visibility = options["visibility"]

        if ( "parent-id" in options ):
            self.parent_id = options["parent-id"]

        if ( "position" in options ):
            self.position = options["position"]

        if ( "render-border" in options ):
            self.render_border = ( int( options["render-border"] ) == 1 )

        if ( "fill" in options ):
            self.fill = options["fill"]

        if ( "uses-title-bar" in options ):
            self.uses_title_bar = ( int( options["uses-title-bar"] ) == 1 )

        if ( "uses-lightbox" in options ):
            self.uses_lightbox = ( int( options["uses-lightbox"] ) == 1 )


        if ( "alpha-controller" in options ):
            self.alpha_controller.configure( options["alpha-controller"] )


        # For chaining
        return self


    # Configure CSS properties
    def css(self, options):

        # Flag as dirty, as we're potentially changing CSS class/state
        self.dirty = True

        # Invalidate any cached metric (we may be changing padding, margin, etc.)
        self.invalidate_cached_metrics()


        # Check for full bloodline
        if ( "bloodline" in options ):

            # Add this widget's selector type to the bloodline
            self.bloodline = "%s>%s" % ( options["bloodline"], "" )#self.get_selector() )

            # In case this is the first in the bloodline, strip leading > (e.g. >rowmenu -> rowmenu)
            self.bloodline = self.bloodline.lstrip(">")

        # Class / state
        if ( "css-class" in options ):
            self.css_class = options["css-class"]

        if ( "class" in options ):
            self.css_class = options["class"]

        if ( "css-state" in options ):
            self.css_state = options["css-state"]

        if ( "state" in options ):
            self.css_state = options["state"]


        # CSS style attributes
        if ( "gradient" in options ):
            self.gradient = options["gradient"]

        if ( "gradient-start" in options ):
            self.gradient_start = options["gradient-start"]

        if ( "gradient-end" in options ):
            self.gradient_end = options["gradient-end"]

        if ( "background-color" in options ):
            self.background_color = options["background-color"]

        if ( "background-alpha" in options ):
            self.background_alpha = float( options["background-alpha"] )

        if ( "rounded-corners" in options ):
            self.rounded_corners = ( int( options["rounded-corners"] ) == 1 )

        if ( "border" in options ):
            self.border_color = options["border"]

        if ( "border-size" in options ):
            self.border_size = int( options["border-size"] )

        if ( "shadow" in options ):
            self.shadow_color = options["shadow"]

        if ( "shadow-size" in options ):
            self.shadow_size = int( options["shadow-size"] )

        if ( "color" in options ):
            self.color = options["color"]

        if ( "text-align" in options ):
            self.text_align = options["text-align"]

        if ( "bbcode" in options ):

            # Let's loop through and copy over each individual definition
            for key in options["bbcode"]:

                # I'm doing this so that I don't keep a refcount on the source hash 
                self.bbcode[key] = options["bbcode"][key]


        # Global margin specifier
        if ( "margin" in options ):

            # Both get the same value
            self.margin_top = int( options["margin"] )
            self.margin_bottom = int( options["margin"] )

        # Explicit assignments
        if ( "margin-top" in options ):
            self.margin_top = int( options["margin-top"] )

        if ( "margin-bottom" in options ):
            self.margin_bottom = int( options["margin-bottom"] )


        # Global padding specifier
        if ( "padding" in options ):

            # All sides get the same value
            self.padding_top = int( options["padding"] )
            self.padding_right = int( options["padding"] )
            self.padding_bottom = int( options["padding"] )
            self.padding_left = int( options["padding"] )

        # Explicit assignments
        if ( "padding-top" in options ):
            self.padding_top = int( options["padding-top"] )

        if ( "padding-right" in options ):
            self.padding_right = int( options["padding-right"] )

        if ( "padding-bottom" in options ):
            self.padding_bottom = int( options["padding-bottom"] )

        if ( "padding-left" in options ):
            self.padding_left = int( options["padding-left"] )


        # For chaining
        return self


    # Get parent widget
    def get_parent(self):

        # Return
        return self.parent


    # Check to see if this widget has a parent
    def has_parent(self):

        # Simple check
        return (self.parent != None)


    # Get earliest ancestor
    def get_top_parent(self):

        # Get handle to parent
        parent = self.get_parent()

        # Validate
        if (parent != None):

            # Check for a higher parent
            if ( parent.has_parent() ):

                # Recursive logic
                return parent.get_top_parent()

            # If this widget's parent has no parent, then
            # we've found the top-most parent.
            else:
                return parent

        # No parent exists
        return None


    # Set parent widget
    def set_parent(self, widget):

        # Set
        self.parent = widget


    # Get namespace for this widget
    def get_namespace(self):

        # Return
        return self.namespace


    # Set namespace for this widget
    def set_namespace(self, namespace):

        # Set
        self.namespace = namespace


    # Get a list of child widgets within this Widget.
    # By default, we assume none, an empty list.
    def get_child_widgets(self):

        # Assume.  Overwrite in inheriting Widgets that contain other Widgets.
        return []


    # Get base CSS selector
    def get_selector(self):

        # If we have a class on this widget, we'll need to append it (e.g. widget.myclass1)
        if (self.css_class != ""):

            # Force :disabled state when applicable, irregardless of css_state
            if (self.disabled):

                return "%s.%s:disabled" % (self.selector, self.css_class)

            # Otherwise, check for css state...
            elif (self.css_state != ""):

                return "%s.%s:%s" % (self.selector, self.css_class, self.css_state)

            # No state at all; return selector and class
            else:

                return "%s.%s" % (self.selector, self.css_class)

        # Otherwise, we're just a run-of-the-mill widget (e.g. rowmenu, label, etc.)
        else:

            # Force :disabled state when applicable, irregardless of css_state
            if (self.disabled):

                return "%s:disabled" % self.selector

            # Otherwise, check for state...
            elif (self.css_state != ""):

                return "%s:%s" % (self.selector, self.css_state)

            # Nope
            else:

                return self.selector


    # Get CSS bloodline
    def get_bloodline(self):

        return "%s%s" % ( self.bloodline, self.get_selector() )


    # Set an attribute
    def set_attribute(self, key, value):

        if ( "xxdebug" in self.attributes ):

            if ( key == "template-version" ):

                if ( value == "not-equipped" ):

                    log ( self.attributes )
                    log(5/0)

        self.attributes[key] = value


        # For chaining
        return self


    # Set multiple attributes
    def set_attributes(self, attributes):

        # Loop
        for key in attributes:

            self.set_attribute(key, attributes[key])


        # For chaining
        return self


    # Get an attribute
    def get_attribute(self, key):

        # Validate
        if (key in self.attributes):

            return self.attributes[key]

        # Couldn't find it?
        else:

            return None


    # Get all attributes
    def get_attributes(self):

        return self.attributes


    # Get "gradient" information.  If this widget does not use a gradient,
    # we will supply the "background color" as start/end to "fake" the desired effect.
    def get_gradient_start(self):

        # Plain background without gradient
        if ( self.gradient in ("", "none") ):

            return self.background_color

        # Truly a gradient
        else:

            return self.gradient_start

    def get_gradient_end(self):

        # Plain background without gradient
        if ( self.gradient in ("", "none") ):

            return self.background_color

        # Truly a gradient
        else:

            return self.gradient_end


    # Get gradient alpha factor...
    def get_background_alpha(self):

        return self.background_alpha


    # Get whether or not this widget's background uses rounded corners
    def get_has_rounded_corners(self):

        return self.rounded_corners


    # Get gradient direction
    def get_gradient_direction(self):

        if ( self.gradient == "left-to-right" ):

            return DIR_RIGHT

        elif ( self.gradient == "right-to-left" ):

            return DIR_LEFT

        elif ( self.gradient == "top-to-bottom" ):

            return DIR_DOWN

        elif ( self.gradient == "bottom-to-top" ):

            return DIR_UP

        # I guess we'll default to DIR_RIGHT
        else:

            return DIR_RIGHT


    # Get border size / color
    def get_border_size(self):

        return self.border_size

    def get_border_color(self):

        return self.border_color


    # Get border shadow size/color
    def get_shadow_size(self):

        return self.shadow_size

    def get_shadow_color(self):

        return self.shadow_color


    # Get text color
    def get_color(self):

        return self.color

    # Get text alignment
    def get_text_align(self):

        return self.text_align

    # Get bbcode data
    def get_bbcode(self):

        return self.bbcode


    # Margin stuff
    def get_margin_top(self):

        return self.margin_top

    def get_margin_bottom(self):

        return self.margin_bottom


    # Padding stuff
    def get_padding_top(self):

        return self.padding_top

    def get_padding_right(self):

        return self.padding_right

    def get_padding_bottom(self):

        return self.padding_bottom

    def get_padding_left(self):

        return self.padding_left


    # Configure the alpha controller; by default, adjust only the local alpha controller.  Overwrite on a per-widget basis as necessary (e.g. for handling cascades)...
    def configure_alpha_controller(self, options):

        # Configure the alpha controller
        self.alpha_controller.configure(options)


    # Get widget id
    def get_id(self):

        return self.id


    # Set widget id
    def set_id(self, widget_id):

        if ( not self.is_locked() ):

            self.id = widget_id


    # Get widget rel attribute
    def get_rel(self):

        return self.rel


    # Widget location
    def get_x(self):

        # Check cache
        metric = self.get_cached_metric("x")

        # Cached?
        if (metric != None):

            return metric

        # Compute
        else:

            # Evaluate x value
            x = evaluate_spatial_expression(
                value = self.x,
                ceiling = self.max_width
            )

            # Cache
            self.cache_metric("x", x)

            # Return
            return x


    def get_y(self):

        # Check cache
        metric = self.get_cached_metric("y")

        # Cached?
        if (metric != None):

            return metric

        # Compute
        else:

            # Evaluate x value
            y = evaluate_spatial_expression(
                value = self.y,
                ceiling = self.max_height
            )

            # Cache
            self.cache_metric("y", y)

            # Return
            return y

        # For now...
        #return int(self.y)

        """
        # Check cache
        metric = self.get_cached_metric("y")

        # Cached?
        if (metric != None):

            return metric

        # Compute
        else:

            # Evaluate y value
            y = evaluate_spatial_expression(
                value = self.y,
                ceiling = self.max_height
            )

            # Cache
            self.cache_metric("y", y)

            # Return
            return y
        """

    # Widget dimensions
    def get_width(self):

        # Check cache
        metric = self.get_cached_metric("width")

        # Cached?
        if (metric != None):

            return metric

        # Compute
        else:

            # Evaluate width value
            width = evaluate_spatial_expression(
                value = self.width,
                ceiling = self.max_width
            )

            # Cache
            self.cache_metric("width", width)


            # Fire resize event
            #self.on_resize(None)


            # Return
            return width


    def get_height(self, text_renderer):

        # Check cache
        metric = self.get_cached_metric("height")

        # Cached?
        if (metric != None):

            return metric

        # Compute
        else:

            # Evaluate height value
            height = evaluate_spatial_expression(
                value = self.height,
                ceiling = self.max_height
            )

            # Cache
            self.cache_metric("height", height)


            # Fire resize event
            #self.on_resize(text_renderer)


            # Return
            return height


    # Default
    def get_max_x(self, text_renderer):

        return 0


    # Widgets will have standard processing common to all widgets (CSS management, etc.)
    def __std_process__(self, control_center, universe):

        # Events that result from standard processing
        results = EventQueue()


        # If we're dirty, we need to get / update CSS data...
        if (self.dirty):

            # Update css
            self.__std_update_css__(control_center, universe)

            #if ( self.css_class == "debug1" ):
            #    log( "I, ", self, "am clean now!" )

            # No longer dirty
            self.dirty = False



        #print "**", self, self.alpha_controller.get_interval(), " / ", self.alpha_controller.get_target()

        # Process alpha
        results.append(
            self.alpha_controller.process().inject_params({
                "widget": self
            })
        )


        # Process slide controllers
        results.append(
            self.hslide_controller.process()
        )

        results.append(
            self.vslide_controller.process()
        )


        #if ( len(results._get_queue()) > 0 ):
        #    log( 5/0 )


        # Return events
        return results


    def __std_post_process__(self, control_center, universe):

        return


    # Widgets can update their CSS when necessary
    def __std_update_css__(self, control_center, universe):

        # First, reset everything to default
        self.__reset_css__()

        # Invalidate any cached metric; we may be changing padding, margin, etc.
        self.invalidate_cached_metrics()


        #print "**update by bloodline:\n\t", self, self.get_bloodline()
        # Now let's use the CSS controller to grab this widget's current style information, according to this widget's bloodline...
        self.css(
            control_center.get_window_controller().get_css_controller().get_properties(
                self.get_bloodline()
            )
        )


    # Render the default background/border for a widget.  Widgets can use this if they just need something simple...
    def __std_render_border__(self, rx, ry, width, height, window_controller, rounded = True):

        alpha = self.alpha_controller.get_interval()

        alpha_factor = self.get_background_alpha()#rowmenu.get_gradient_alpha_factor(disabled = disabled, highlight = highlighted)

        # Don't bother "rendering" when fully-transparent
        if (alpha_factor > 0):

            if (rounded):


                # Render background
                window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                    rx,
                    ry,
                    width,
                    height,
                    background1 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_start() ), #rowmenu.get_gradient_color1(disabled = disabled, highlight = highlighted)),
                    background2 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_end() ), #rowmenu.get_gradient_color2(disabled = disabled, highlight = highlighted)),
                    border = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ), #rowmenu.get_border(disabled = disabled, highlight = highlighted)),
                    border_size = 0,#rowmenu.get_border_size(), #rowmenu.get_border_size(disabled = disabled, highlight = highlighted),
                    shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ), #rowmenu.get_shadow(disabled = disabled, highlight = highlighted)),
                    shadow_size = 0,#rowmenu.get_shadow_size(), #rowmenu.get_shadow_size(disabled = disabled, highlight = highlighted),
                    gradient_direction = self.get_gradient_direction(), #rowmenu.get_gradient_direction(disabled = disabled, highlight = highlighted),
                    radius = 10
                )

                # Render frame
                window_controller.get_geometry_controller().draw_rounded_rect_frame(
                    rx,
                    ry,
                    width,
                    height,
                    color = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ), #rowmenu.get_border(disabled = disabled, highlight = highlighted)),
                    border_size = self.get_border_size(), #rowmenu.get_border_size(disabled = disabled, highlight = highlighted),
                    shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ), #rowmenu.get_shadow(disabled = disabled, highlight = highlighted)),
                    shadow_size = self.get_shadow_size(), #rowmenu.get_shadow_size(disabled = disabled, highlight = highlighted),
                    radius = 10
                )

            else:

                # Render background
                window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(
                    rx,
                    ry,
                    width,
                    height,
                    set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_start() ),
                    set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_end() )
                )

                # Render frame
                if ( self.get_border_size() > 0 ):

                    window_controller.get_geometry_controller().draw_rect_frame(
                        rx,
                        ry,
                        width,
                        height,
                        set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ),
                        self.get_border_size()
                    )

                    # Render frame "shadow"
                    if ( self.get_shadow_size() > 0 ):

                        window_controller.get_geometry_controller().draw_rect_frame(
                            rx + self.get_border_size(),
                            ry + self.get_border_size(),
                            width - (2 * self.get_border_size()),
                            height - (2 * self.get_border_size()),
                            set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ),
                            self.get_shadow_size()
                        )


    # Render the default border for a widget.  Widgets can use this if they just need something simple...
    def __std_render_frame__(self, rx, ry, width, height, window_controller):

        alpha = self.alpha_controller.get_interval()

        alpha_factor = self.get_background_alpha()#rowmenu.get_gradient_alpha_factor(disabled = disabled, highlight = highlighted)

        # Render frame
        window_controller.get_geometry_controller().draw_rounded_rect_frame(
            rx,
            ry,
            width,
            height,
            color = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ), #rowmenu.get_border(disabled = disabled, highlight = highlighted)),
            border_size = self.get_border_size(), #rowmenu.get_border_size(disabled = disabled, highlight = highlighted),
            shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ), #rowmenu.get_shadow(disabled = disabled, highlight = highlighted)),
            shadow_size = self.get_shadow_size(), #rowmenu.get_shadow_size(disabled = disabled, highlight = highlighted),
            radius = 10
        )


    # Render the default background behind the entirety of a given widget
    def __std_render_fill__(self, rx, ry, width, height, window_controller):

        alpha = self.alpha_controller.get_interval()

        alpha_factor = self.get_background_alpha()#rowmenu.get_gradient_alpha_factor(disabled = disabled, highlight = highlighted)

        # Render background
        window_controller.get_geometry_controller().draw_rect_with_gradient(
            rx,
            ry,
            width,
            height,
            color1 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_start() ),
            color2 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_end() ),
            gradient_direction = self.get_gradient_direction()
        )


    # Cache a given metric (e.g. "height")
    def cache_metric(self, metric, value):

        self.cached_metrics[metric] = value


    # Clear cached metrics
    def invalidate_cached_metrics(self):

        # Clear this widget's cache
        self.cached_metrics.clear()


        # Clear any child widget's metrics, also
        for widget in self.get_child_widgets():

            # Descend
            widget.invalidate_cached_metrics()


    # Try to retrieve a cached metric
    def get_cached_metric(self, metric):

        # Found it?
        if (metric in self.cached_metrics):

            return self.cached_metrics[metric]

        # Report that we didn't find it...
        else:

            return None


    # Get the entire height of the widget (including margin)
    def get_box_height(self, text_renderer):

        # Try to get the cached copy
        metric = self.get_cached_metric("box-height")

        # Cached already?
        if (metric != None):

            return metric

        # Nope... gotta compute it and cache it
        else:

            # Compute
            total = self.get_margin_top() + self.get_render_height(text_renderer) + self.get_margin_bottom()

            # Cache
            self.cache_metric("box-height", total)

            #print "widget '%s' reports box height %d" % (self.get_bloodline(), total)

            #print total, self.get_padding_top(), self.get_padding_bottom()

            #if (self.css_class == "min1"):
            #    log2( "my box height is %d + %d + %d" % ( self.get_margin_top(), self.get_render_height(text_renderer), self.get_margin_bottom() ) )

            # Fire the resize callback
            #self.on_resize(text_renderer)

            # Return now
            return total


    # Get the "rendered" height of the widget (i.e. everything but the margin)
    def get_render_height(self, text_renderer):

        # Cached?
        metric = self.get_cached_metric("render-height")

        # Found it?
        if (metric != None):

            return metric

        # No, let's calculate and cache
        else:

            # Calculate... padding (top and bottom) plus the height required by this widget
            total = self.get_padding_top() + self.report_widget_height(text_renderer) + self.get_padding_bottom()

            #print "widget '%s' reports render height %d" % (self.get_bloodline(), total)

            # Cache
            self.cache_metric("render-height", total)

            # Fire a resize callback
            #self.on_resize(text_renderer)

            # Return
            return total


    # Any widget that renders to screen (i.e. most everything except key listeners, etc.)
    # should overwrite these methods to report their computed width/height...
    def report_widget_width(self, text_renderer):

        return 0

    def report_widget_height(self, text_renderer):

        return 0


    # Lock controller
    def lock(self):

        self.lock_count += 1

        # We should also lock the slide controllers
        self.hslide_controller.lock()
        self.vslide_controller.lock()

        # as well as the alpha controller
        self.alpha_controller.lock()


    # Unlock
    def unlock(self):

        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            self.lock_count = 0


        # We should also unlock the slide controllers
        self.hslide_controller.unlock()
        self.vslide_controller.unlock()

        # and the alpha controller
        self.alpha_controller.unlock()


    # Lock status
    def is_locked(self):

        return (self.lock_count > 0)


    # Show a widget (fade in)
    def show(self, target = 0.9, animated = True, on_complete = ""):

        # Don't touch locked Widgets
        if ( not self.is_locked() ):

            # Skip animation, showing it at full opacity immediately?
            if (not animated):

                # Set interval to given target
                self.alpha_controller.set_interval(target)

            # Summon alpha controller
            self.alpha_controller.summon(target = target, on_complete = on_complete)

            # Callback
            self.on_show(target, animated, on_complete = "")


    # On show callback
    def on_show(self, target, animated, on_complete):

        # Loop child widgets
        for widget in self.get_child_widgets():

            # Show child widget
            widget.show(target, animated, on_complete)


    # While awake (i.e. visible) callback
    def while_awake(self):

        # Loop child widgets
        for widget in self.get_child_widgets():

            # Awake
            widget.while_awake()


    # Hide a widget (fade out)
    def hide(self, target = 0.0, animated = True, on_complete = ""):

        # Don't touch locked Widgets
        if ( not self.is_locked() ):

            # Skip animation, hiding it immediately?
            if (not animated):

                # Set interval to given target
                self.alpha_controller.set_interval(target)

            # Configure alpha controller to fade out
            self.configure_alpha_controller({
                "target": target,
                "on-complete": on_complete
            })

            # Callback
            self.on_hide(target, animated, on_complete = "")


    # On hide callback
    def on_hide(self, target, animated, on_complete):

        # Loop child widgets
        for widget in self.get_child_widgets():

            # Hide child widget
            widget.hide(target, animated, on_complete)


    # While asleep (i.e. not visible) callback
    def while_asleep(self):

        # Loop child widgets
        for widget in self.get_child_widgets():

            # Forward
            widget.while_asleep()


    # Give focus to a widget
    def focus(self):

        # No point in changing state if we already have focus
        if (not self.has_focus):

            # Flag
            self.has_focus = True

            # Update css state
            self.css({
                "state": "active"
            })


        # Callback
        self.on_focus()


    # On focus callback
    def on_focus(self):

        log(
            "Bloodline:  %s" % self.get_bloodline()
        )

        # Update bloodline for all children
        for widget in self.get_child_widgets():

            # Each needs a refresh
            widget.css({
                "bloodline": self.get_bloodline()
            }).focus()


    # Remove focus from a widget
    def blur(self):

        # No point in changing state if we're already blurred
        if (self.has_focus):

            # Flag
            self.has_focus = False

            # Update css state
            self.css({
                "state": ""
            })


        # Callback
        self.on_blur()


    # On blur callback
    def on_blur(self):

        # Update bloodline for all children
        for widget in self.get_child_widgets():

            # Each needs a refresh
            widget.css({
                "bloodline": self.get_bloodline()
            }).blur()


    # Determine if a widget has focus
    def is_focused(self):

        # Check focus state
        return self.has_focus


    # Slide the widget to a given direction by a given amount or percentage (0.0 - 1.0+) of the widget's width
    def slide(self, direction, amount = 0, percent = None, delay = 0, animated = True, incremental = False, on_complete = ""):

        if ( not self.is_locked() ):

            # Unslide?
            if ( direction == None):

                # This is going to be a little hacky
                if ( self.hslide_controller.get_interval() != 0 ):

                    # Configure settings for both slide controllers
                    self.hslide_controller.configure({
                        "target": 0,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Zap?
                    if (not animated):

                        self.hslide_controller.configure({
                            "interval": 0
                        })

                elif ( self.vslide_controller.get_interval() != 0 ):

                    self.vslide_controller.configure({
                        "target": 0,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Zap?
                    if (not animated):

                        self.vslide_controller.configure({
                            "interval": 0
                        })

                # It's already at the "None" unslide position, but we can forward the on-complete event to the hslide controller (arbitrary, they're both at 0 anyway)
                else:

                    # Animation is irrelevant, it's not going anywhere anyway
                    self.hslide_controller.configure({
                        "target": 0,
                        "delay": delay,
                        "on-complete": on_complete
                    })



            # Horizontal slide?
            if ( direction in (DIR_LEFT, DIR_RIGHT) ):

                # If we specified any kind of percentage, then we'll use that to set / override the amount
                if (percent != None):

                    # If this is an incremental slide, then we'll add the calculated amount to the existing slide value
                    if (incremental):

                        amount = self.hslide_controller.get_interval() + int( percent * self.get_width() )

                    # Otherwise, it's a set value...
                    else:

                        amount = int( percent * self.get_width() )

                elif (incremental):

                    amount = self.hslide_controller.get_interval() + amount


                # Slide left
                if (direction == DIR_LEFT):

                    # Configure settings
                    self.hslide_controller.configure({
                        "target": -amount,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Sometimes we just want to "zap" the thing over immediately (usually to give it an "initial position"
                    # from which it will then "slide in" or something...)
                    if (not animated):

                        self.hslide_controller.configure({
                            "interval": -amount
                        })


                # Slide right
                elif (direction == DIR_RIGHT):

                    # Configure settings
                    self.hslide_controller.configure({
                        "target": amount,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Instant "zap" slide
                    if (not animated):

                        self.hslide_controller.configure({
                            "interval": amount
                        })


                # No slide; return to default location
                elif (direction == None):

                    # Configure settings
                    self.hslide_controller.configure({
                        "target": 0,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Zap?
                    if (not animated):

                        self.hslide_controller.configure({
                            "interval": 0
                        })


            # Vertical slide?
            if ( direction in (DIR_UP, DIR_DOWN) ):

                # For now, I'm not going to support percentage-based vertical slides (no text renderer param).  Incremental is fine, though...
                if (incremental):

                    amount = self.vslide_controller.get_interval() + amount


                # Slide up
                if (direction == DIR_UP):

                    # Configure settings
                    self.vslide_controller.configure({
                        "target": -amount,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Sometimes we just want to "zap" the thing over immediately (usually to give it an "initial position"
                    # from which it will then "slide in" or something...)
                    if (not animated):

                        self.vslide_controller.configure({
                            "interval": -amount
                        })


                # Slide down
                elif (direction == DIR_DOWN):

                    # Configure settings
                    self.vslide_controller.configure({
                        "target": amount,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Instant "zap" slide
                    if (not animated):

                        self.vslide_controller.configure({
                            "interval": amount
                        })


                # No slide; return to default location
                elif (direction == None):

                    # Configure settings
                    self.vslide_controller.configure({
                        "target": 0,
                        "delay": delay,
                        "on-complete": on_complete
                    })

                    # Zap?
                    if (not animated):

                        self.vslide_controller.configure({
                            "interval": 0
                        })
