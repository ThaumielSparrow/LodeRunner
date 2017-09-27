from code.ui.common import UIWidget

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLNode

from code.utils.common import log, log2, xml_encode, xml_decode, evaluate_spatial_expression

from code.constants.common import STENCIL_MODE_NONE, STENCIL_MODE_PAINT, STENCIL_MODE_ERASE, STENCIL_MODE_PAINTED_ONLY, STENCIL_MODE_UNPAINTED_ONLY

# A WidgetContainer will hold some number of UIWidgets.
class Box(UIWidget):

    def __init__(self, selector = "box"):

        # We don't actually render the container itself, so the CSS is irrelevant for the most part,
        # but I want to make it part of the "DOM" chain, if you will.
        UIWidget.__init__(self, selector = selector)


        # Alignment for the container itself
        self.align = "left" # left, center, right

        # A widget container can align its contents (perhaps centering elements if they do not require the entire width)
        self.content_align = "left" # left, center, right


        # We can place a tooltip widget (any Widget) on a Box
        self.tooltip = None


        # List of widgets
        self.widgets = []


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "align" in options ):
            self.align = options["align"]

        if ( "content-align" in options ):
            self.content_align = options["content-align"]


        # ** WHY WOULD I DO THIS???
        """
        ## Funnel configuration options forward to all widgets
        #for widget in self.get_widgets():
        #    widget.configure(options)
        """


        # For chaining
        return self


    # Configure the alpha controller, then cascade
    def configure_alpha_controller(self, options):

        # Standard alpha configuration
        UIWidget.configure_alpha_controller(self, options)

        # Cascade to children
        for widget in self.widgets:

            # Cascade
            widget.configure_alpha_controller(options)


    # Save box state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Add in state of any child widget (members of the container)
        descendants_node = root.add_node(
            XMLNode("descendants")
        )

        # Loop each widget
        for i in range( 0, len(self.widgets) ):

            # Convenience
            widget = self.widgets[i]


            # Prepare to save widget state
            widget_node = descendants_node.add_node(
                XMLNode("descendant")
            )


            # Track index
            widget_node.set_attribute("index", i)

            # Add widget state
            widget_node.add_node(
                widget.save_state()
            )


        # Return node
        return root


    # Load Box state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Grab descendant data
        descendants_node = node.find_node_by_tag("descendants")

        # Validate
        if (descendants_node):

            # Loop through all widgets
            descendant_collection = descendants_node.get_nodes_by_tag("descendant")

            for ref_descendant in descendant_collection:

                # Get widget list index
                index = int( ref_descendant.get_attribute("index") )

                # Sanity
                if ( index < len(self.widgets) ):

                    # Restore given widget
                    self.widgets[index].load_state(
                        ref_descendant.find_node_by_tag("widget")
                    )


    # Get child widgets
    def get_child_widgets(self):

        # Track results
        results = []

        # Grab child widgets
        results.extend(self.widgets)

        """
        # Tooltip available?
        if (self.tooltip):

            # Add
            results.append(self.tooltip)
        """

        # Return all widgets
        return results


    # Get tooltip
    def get_tooltip(self):

        # Return
        return self.tooltip


    # Count widgets in this Box
    def count(self):

        return len(self.widgets)


    # Grab all widgets
    def get_widgets(self):

        return self.widgets


    # Add a new widget to this Box
    def add_widget(self, widget):

        # Hello, friend!
        self.widgets.append(
            widget.configure({
                "bloodline": self.get_bloodline()
            })
        )

        # For chaining
        return self.widgets[-1]


    # Get a particular widget
    def get_widget_by_id(self, widget_id):

        # Loop widgets
        for widget in self.get_child_widgets():

            # Match?
            if ( widget.get_id() == widget_id ):

                # Return Widget
                return widget


        # Couldn't find it
        return None


    # Try to find a widget somewhere within the box, even if it's in another widget
    def find_widget_by_id(self, widget_id):

        # Check each widget
        for widget in self.get_child_widgets():

            # Is this the one?
            if ( widget.get_id() == widget_id ):

                # Yes!
                return widget

            # If not, perhaps the widget contains the desired widget...
            else:

                # Try to find it...
                nested_widget = widget.find_widget_by_id(widget_id)

                # Find one?
                if (nested_widget):

                    # Here it is
                    return nested_widget

        # We couldn't find a widget by that id...
        return None


    # Alias
    def translate(self, h):
        self.translate_environment_variables(h)

    # Translate a given hash of environment variables
    def translate_environment_variables(self, h):

        # Loop children
        for widget in self.get_child_widgets():

            # Do not descend into new namespaces
            if ( widget.get_namespace() == None ):

                # Translate child widget
                widget.translate_environment_variables(h)


        # Does this box have a tooltip?
        if (self.tooltip):

            # Do not descend into new namespaces
            if ( self.tooltip.get_namespace() == None ):

                # Translate tooltip
                self.tooltip.translate_environment_variables(h)


        # This widget only contains other widgets; it will not translate
        # anything of its own self.


    # Box uses a custom while awake callback to handle tooltip logic
    def on_focus(self):

        # Standard callback
        UIWidget.on_focus(self)

        # Tooltip?
        if (self.tooltip):

            # Cascade
            self.tooltip.css({
                "bloodline": self.get_bloodline()
            }).focus()


    # Box uses a custom while asleep callback to handle tooltip logic
    def on_blur(self):

        # Standard callback
        UIWidget.on_blur(self)

        # Tooltip?
        if (self.tooltip):

            # Cascade
            self.tooltip.css({
                "bloodline": self.get_bloodline()
            }).blur()


    # On a resize, we should send each widget inside of this container a new max-width
    def on_resize(self, text_renderer = None):

        # Cascade
        for widget in self.get_child_widgets():

            widget.configure({
                "max-width": self.get_width() - ( self.get_padding_left() + self.get_padding_right() )
            })

            if (text_renderer):

                widget.configure({
                    "max-height": self.report_widget_height(text_renderer)#self.get_render_height(text_renderer) - ( self.get_padding_top() + self.get_padding_bottom() )
                })

            widget.on_resize(text_renderer)


        # If this Box has a tooltip, let's set a max width (?)
        if (self.tooltip):

            # I guess ...
            self.tooltip.configure({
                "max-width": self.get_width() - ( self.get_padding_left() + self.get_padding_right() )
            })

            # Resize callback
            self.tooltip.on_resize(text_renderer)


    # When "selected," a container will check with its widgets to see if they have any "on select" reaction
    def on_select(self):

        # Track events
        results = EventQueue()

        for widget in self.get_widgets():

            widget_results = widget.on_select()

            if (widget_results != None):

                # We need to inject "this" (self) into the params...
                for widget_result in widget_results._get_queue():

                    widget_result.set_params({
                        "widget": self
                    })

                # Append modified results
                results.append(
                    widget_results
                )

        # Return events
        return results


    def report_widget_width(self, text_renderer):

        return self.width


    def report_widget_height(self, text_renderer):

        metric = self.get_cached_metric("reported-widget-height")

        if (metric != None):

            return metric

        else:

            # Some boxes (when in homogenized RowMenu Group widgets) will use a pre-assigned height value
            if ( self.style_height > 0 ):

                # Easy
                metric = self.style_height

            elif ( len(self.widgets) > 0 ):

                metric = max(
                    self.min_height,
                    max( ( widget.get_y() + widget.get_box_height(text_renderer) ) for widget in self.get_child_widgets() if widget.position == "relative" )
                )

            else:

                metric = self.min_height

            # Cache for future reuse
            self.cache_metric("reported-widget-height", metric)

            if ( self.css_class == "debug1" ):
                log2( self.get_rel(), "reports height:  %s" % metric )

            # Return value
            return metric


    def get_min_x(self, text_renderer):

        min_x = 0

        if ( len(self.widgets) > 0 ):

            min_x = min(widget.get_x() + widget.get_x_offset(text_renderer) for widget in self.get_widgets() if widget.position == "relative")

        return min_x


    def get_max_x(self, text_renderer):

        max_x = 0

        if ( len(self.widgets) > 0 ):

            max_x = max( widget.get_max_x(text_renderer) for widget in self.get_widgets() if widget.position == "relative" )

        return max_x


    def populate_from_collection(self, elem_collection, control_center, universe):

        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        for ref_elem in elem_collection:

            """
            (x, y, w, h) = (
                0,
                int( ref_elem.get_attribute("y") ),
                self.width,
                0 # Updated later...
            )


            # Width calculation
            if (ref_elem.get_attribute("width")):

                ref_elem.set_attributes({
                    "width": evaluate_spatial_expression(
                        value = ref_elem.get_attribute("width"),
                        ceiling = self.width
                    )
                })

            # X-coordinate calculation
            if (ref_elem.get_attribute("x")):

                ref_elem.set_attributes({
                    "x": evaluate_spatial_expression(
                        value = ref_elem.get_attribute("x"),
                        ceiling = self.width
                    )
                })

            # Y-coordinate calculation
            #if (ref_elem.get_attribute("y")):

            #    y = evaluate_spatial_expression(
            #        value = ref_elem.get_attribute("y"),
            #        ceiling = self.calculate_height(text_renderer)
            #    )
            """


            # Update the bloodline data
            ref_elem.set_attributes({
                "bloodline": self.get_bloodline(),
                "max-width": self.get_width()
            })

            # Create the raw widget
            widget = widget_dispatcher.convert_node_to_widget(ref_elem, control_center, universe)

            # Validate that we could translate the node into a widget
            if (widget):

                # Set parent to this Box
                widget.set_parent(self)

                # Create and configure the widget (position)
                self.add_widget(widget).configure(
                    #ref_elem.set_attributes({
                    #    "bloodline": self.get_bloodline(), # Assign the widget its CSS bloodline (it belongs to the RowMenu, then a RowMenuGroup)
                    #    "xx": 0,#x,
                    #    "xy": 0#y
                    #}).get_attributes()
                    {
                        "bloodline": self.get_bloodline()
                    }
                )

            else:
                log( "Unknown widget tag '%s'" % ref_elem.tag_type )

        self.on_resize( control_center.get_window_controller().get_default_text_controller().get_text_renderer() )


    def handle_user_input(self, control_center, universe):

        # One of the widgets may signal various events (e.g. KeyListeners signalling key presses)
        results = EventQueue()

        for widget in self.get_widgets():

            # Send input to widget
            results.append(
                widget.handle_user_input(control_center, universe)
            )


        # Return events
        return results


    def process(self, control_center, universe):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Process each widget in this container
        for widget in self.get_widgets():

            # Process widget
            results.append(
                widget.process(control_center, universe)
            )


        # Does this Box have a tooltip widget?
        if (self.tooltip):

            # Let's just process it without events, huh?
            self.tooltip.process(control_center, universe)


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Box rendering position
        (rx, ry) = (
            sx + self.get_x() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_margin_top() + self.vslide_controller.get_interval()
        )

        #(u, v) = (sx, sy)
        (zx, zy) = (rx, ry)

        # Current box dimensions
        (width, height) = (
            self.get_width(),
            max( self.min_height, self.get_render_height(text_renderer) )
        )

        """
        # Hacky overwrite
        if (self.style_height > 0):

            # Overwrite
            height = self.style_height
        """


        # Custom containre alignment
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        elif (self.align == "right"):

            rx -= self.get_width()


        # Use our own alpha value
        alpha = self.alpha_controller.get_interval()


        # Fetch stencil controller
        stencil_controller = window_controller.get_stencil_controller()


        # Clear it
        #stencil_controller.clear()

        # Enable painting, as we prepare to define the renderable area
        #stencil_controller.set_mode(STENCIL_MODE_PAINT)

        # Now, render the border, if/a
        if (self.render_border):

            self.__std_render_border__(rx, ry, width, height, window_controller)

        # Set the stencil controller to erase mode before rendering the border
        #stencil_controller.set_mode(STENCIL_MODE_ERASE)

        # Render the frame itself, in the process marking its frame as un-writeable to anything else (leaving only the inside region as writeable)
        if (self.render_border):

            self.__std_render_frame__(rx, ry, width, height, window_controller)


        #stencil_controller.set_mode(STENCIL_MODE_PAINTED_ONLY)


        #print stencil_controller.get_mode()
        # Render a fill behind the widget's contents?
        if (self.fill == "always"):

            self.__std_render_fill__(rx, ry, width, height, window_controller)
            #print self.get_bloodline()
            #print width, height, self.get_gradient_start(), self.get_gradient_end(), self.get_background_alpha(), self.alpha_controller.get_interval()

        elif ( (self.fill == "active") and ( self.is_focused() ) ):

            self.__std_render_fill__(rx, ry, width, height, window_controller)


        # If this group wants to have a title bar (typically a rectangle under the first item),
        # then we'll BRIEFLY enable stencil testing on the region we just painted to...
        #if (self.uses_title_bar):
        #    stencil_controller.set_mode(STENCIL_MODE_PAINTED_ONLY)

        # Otherwise, forget about the stencil impressions we just painted.
        #else:
        #    stencil_controller.set_mode(STENCIL_MODE_NONE)#PAINTED_ONLY)
        #print stencil_controller.get_mode()

        # Center content?
        if (self.content_align == "center"):

            # Figure out how much of the container's width we really need to use
            max_x = self.get_max_x(text_renderer)

            # If it's less than the container's width...
            if (max_x < width):

                # ... then we can center the contents
                rx += int( (width - max_x) / 2 )

        # Align right?
        elif (self.content_align == "right"):

            # Figure out how much of the container's width we really need to use
            max_x = self.get_max_x(text_renderer)

            # If it's less than the container's width...
            if (max_x < width):

                # ... then we can center the contents
                rx += (width - max_x)#sx += int( (width - max_x) / 2 )

            else:

                rx -= (max_x - width)


        # Base widget rendering position (accounting for box padding)
        (wx, wy) = (
            rx + self.get_padding_left(),
            ry + self.get_padding_top()
        )

        for i in range( 0 , len(self.widgets) ):

            # Convenience
            widget = self.widgets[i]

            # We'll only render the widget when appropriate...
            if ( (widget.display == "constant") or ( widget.display == "on-focus" and self.is_focused() ) or (widget.display == "on-focus:linger" and ( self.is_focused() or widget.linger() )) or (widget.display == "off-focus" and ( not self.is_focused() )) ):

                widget.draw(wx, wy, tilesheet_sprite, additional_sprites, text_renderer, window_controller)
                #text_renderer.render_with_wrap( "%s, %s -> %s" % (widget.selector, widget.x, widget.get_x()), sx, sy + ( (i + 1) * 20 ), (225, 225, 225, 0.75) )
                #i += 1


            # If this widget uses a title bar, then we only apply that "effect" to
            # the leading widget.  After we've rendered it, we stop caring about the stencil test.
            if ( (i == 0) and (self.uses_title_bar) ):

                stencil_controller.set_mode(STENCIL_MODE_NONE)


        # Tooltip?
        if (self.tooltip):

            # Only render the tooltip if this Box has input focus
            if ( self.is_focused() ):

                # Hack
                self.tooltip.draw(rx, ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


        #window_controller.get_geometry_controller().draw_rect( zx, zy, self.get_width(), 20, (25, 25, 225, 0.15) )
        #text_renderer.render_with_wrap( "%d, %d, w = %s, h = %s, calc = %s, max = %s" % (zx, zy, self.width, self.report_widget_height(text_renderer), self.get_width(), self.max_width), rx, ry, (225, 225, 25, 0.75) )

        #if (self.css_class == "debug2"):
        #    text_renderer.render("%s, %s" % (self.alpha_controller.get_interval(), self.alpha_controller.get_target()), rx + 100, ry + 0*text_renderer.font_height, (175, 225, 175, 0.75))
