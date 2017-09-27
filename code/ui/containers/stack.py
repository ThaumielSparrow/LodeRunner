import sys, time

from code.ui.common import UIWidget

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, xml_encode, xml_decode

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, DIR_LEFT, DIR_RIGHT


class Stack(UIWidget):

    def __init__(self):

        UIWidget.__init__(self, selector = "stack")


        self.state_changed = False


        # By default, we'll assume the widget stack uses focus.
        # Some won't, though; some just serve as formatting widgets.
        self.uses_focus = True


        # Keep track of the id of the active widget.  We must have an id for any widget that
        # wants to receive input at any point.
        self.active_widget_id = ""


        # Vertical alignment
        self.valign = "top" # top, center, bottom

        # Padding between sections
        self.pane_padding = 0 # hard-coded


        # Just for record-keeping; we don't actually use this.
        self.cursor = None


        # Widgets in the stack
        self.widgets = []


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "uses-focus" in options ):
            self.uses_focus = ( int( options["uses-focus"] ) == 1 )

        if ( "active-widget-id" in options ):
            self.active_widget_id = options["active-widget-id"]

        if ( "pane-padding" in options ):
            self.pane_padding = int( options["pane-padding"] )

        if ( "valign" in options ):
            self.valign = options["valign"]


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


    # Save Stack state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Add in a few state details specific to this Stack
        details_node = root.add_node(
            XMLNode("stack")
        )

        # Get the ID of the currently-focused widget, assuming we have one...
        widget = self.get_active_widget()

        # Validate
        if (widget):

            # Save properties
            details_node.set_attributes({
                "focused-widget-id": widget.get_id(),
                "active-widget-id": self.active_widget_id
            })


        # Add in state of any child widget (members of the stack)
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

            # Track any attributes we assigned (focused, etc.)
            for key in widget.get_attributes():

                widget_node.set_attribute(
                    key,
                    widget.get_attribute(key)
                )


            # Add widget state
            widget_node.add_node(
                widget.save_state()
            )


        # Return node
        return root


    # Load Stack state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Grab details specific to this HMenu
        details_node = node.find_node_by_tag("stack")

        # Validate
        if (details_node):

            # Get the id of the widget that should be focused, if provided...
            if ( details_node.get_attribute("focused-widget-id") ):

                # Fetch
                widget_id = details_node.get_attribute("focused-widget-id")

                # Try to focus on that widget
                self.set_active_widget_by_id(widget_id)


        # Check for descendant state data
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
                        ref_descendant.get_first_node_by_tag("widget")
                    )


    # Get child widgets
    def get_child_widgets(self):

        # Return all widgets
        return self.widgets


    def save_state_as_xml(self):

        xml = """
            <self has-focus = '%s'>
                #INNERXML
            </self>
        """ % self.has_focus


        # Compile xml for each child item...
        markup = ""

        for i in range( 0, len(self.widgets) ):

            item_markup = """
                <item index = '%d'>
                    #ITEMXML
                </item>
            """ % i

            item_markup = item_markup.replace( "#ITEMXML", self.widgets[i].save_state_as_xml() )

            markup += item_markup


        xml = xml.replace("#INNERXML", markup)

        return xml


    def load_state_from_xml(self, xml):

        # Generic node
        node = XMLParser().create_node_from_xml(xml)

        # Load the cursor data
        ref_self = node.get_first_node_by_tag("self")

        if (ref_self):

            self.has_focus = ( int( ref_self.get_attribute("has-focus") ) == 1 )

            for i in range(0, self.count()):

                ref_item = ref_self.get_first_node_by_tag("item", {"index": "%d" % i})

                if (ref_item):

                    #self.get_item_at_index(i).uses_focus = int( ref_item.get_attribute("uses-focus") )

                    self.widgets[i].load_state_from_xml( ref_item.compile_inner_xml_string() )


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

        # This widget only contains other widgets; it will not translate
        # anything of its own self.


    """ Event callbacks """
    # On birth, the widget should collect all on-birth data from its widgets
    def handle_birth(self):

        # Track events
        results = EventQueue()

        # Check child widgets
        for widget in self.widgets:

            results.append(
                widget.handle_birth()
            )

        # Return events
        return results


    # the Stack widget needs a special on_focus callback.
    # Stack will either give focus only to the active selection, or to no selection (if the stack does not use focus)
    def on_focus(self):

        # We will only give focus to the active member of the stack
        # if this stack cares about user input...
        if (self.uses_focus):

            # Blur all children first
            for widget in self.get_child_widgets():

                # Blur
                widget.css({
                    "bloodline": self.get_bloodline()
                }).focus()
                widget.blur()


            # Get active widget
            widget = self.get_active_widget()

            # Validate
            if (widget):

                # Focus on the active selection
                widget.focus()


        # Otherwise, we'll blur all children (Stack does not care about focus)
        else:

            # Blur every child
            for widget in self.get_child_widgets():

                # Blur
                widget.configure({
                    "bloodline": self.get_bloodline()
                }).focus()
                widget.blur()


    # Note that we just use the inherited on_blur callback.


    # On resize, ths stack should send its children its new max-width
    def on_resize(self, text_renderer = None):

        # Cascade
        for widget in self.widgets:

            widget.configure({
                "max-width": ( self.get_width() - ( self.get_padding_left() + self.get_padding_right() ) )
            })

            widget.on_resize(text_renderer)


    # Count widgets in stack
    def count(self):

        return len(self.widgets)


    def report_widget_height(self, text_renderer):

        metric = self.get_cached_metric("reported-widget-height")

        if (metric != None):

            return metric

        else:

            if ( len(self.widgets) > 0 ):

                metric = sum( (widget.get_box_height(text_renderer) ) for widget in self.widgets )

            else:

                metric = 0

            # Cache metric
            self.cache_metric("reported-widget-height", metric)

            # Return
            return metric


    # Determine y-rendering position of widget N assuming a start of 0
    def get_y_offset_at_index(self, index, text_renderer):

        # Use box height because the stack contains the entirety of each widget
        return sum( (self.pane_padding + widget.get_box_height(text_renderer)) for widget in self.widgets[0: index] )


    # Determine y rendering position of a widget (by its id) assuming a start of 0
    def get_y_offset_by_widget_id(self, widget_id, text_renderer):

        # find the index of the given widget
        for i in range( 0, len(self.widgets) ):

            # Match?
            if ( self.widgets[i].get_id() == widget_id ):

                # Return offset at this index
                return self.get_y_offset_at_index(i, text_renderer)


        # We couldn't find that widget...
        return 0


    # Determine height remaining?
    def get_height_remaining(self, text_renderer):

        return max( 0, (self.height - sum( (self.pane_padding + widget.get_box_height(text_renderer)) for widget in self.widgets)) )


    # Add a widget to the stack
    def add_widget(self, widget, text_renderer):

        if (widget):

            # Set parent on the widget to this Stack
            widget.set_parent(self)

            # Force the width of the widget to equal the stack's width, and update its bloodline
            widget.configure({
                "zwidth": self.width,
                "bloodline": self.get_bloodline()
            })

            # Add to the stack
            self.widgets.append(widget)


            # Configure width on the new widget
            widget.configure({
                "max-width": ( self.get_width() - ( self.get_padding_left() + self.get_padding_right() ) )
            })

            # Fire the new widget's resize callback
            widget.on_resize(text_renderer)
            #self.on_resize()

            self.invalidate_cached_metrics()


            # Return a handle to the new widget
            return widget


    # convenience wrapper
    def add_widget_with_id(self, widget, widget_id, text_renderer):

        # Set the widget's id
        widget.set_id(widget_id)

        # Add an ID attribute to the widget.  We could do this manually before using .add_widget() as well, of course.
        self.add_widget(widget, text_renderer)


    # Remove a specific widget from the stack (better know what you're doing)
    def remove_widget_at_index(self, index):

        # Sanity
        if ( index < len(self.widgets) ):

            # Later...
            return self.widgets.pop(index)


    # Remove a widget by a given ID
    def remove_widget_by_id(self, widget_id):

        # Loop
        i = 0

        while ( i < len(self.widgets) ):

            # Check widget id
            if ( self.widgets[i].get_id() == widget_id ):

                # Later
                return self.widgets.pop(i)

            # Continue looping
            else:
                i += 1


    # Fetch a given widget from the stack by index
    def get_widget_at_index(self, index):

        # Sanity
        if ( index < len(self.widgets) ):

            return self.widgets[index]

        else:

            return None


    # Get a widget by its ID attribute
    def get_widget_by_id(self, widget_id):

        for widget in self.widgets:

            # Check against widget id
            if ( widget.get_id() == widget_id ):

                # Matched
                return widget


        # Couldn't find it!
        return None


    # Try to find a widget nested anywhere within the stack, even if it's in a deeply nested widget
    def find_widget_by_id(self, widget_id):

        # Check each widget
        for widget in self.widgets:

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


    # Get multiple widgets in one call
    def get_widgets_by_ids(self, widget_id_list):

        # Track results
        results = []

        # Try to find each widget id
        for widget_id in widget_id_list:

            # Check for widget
            widget = self.get_widget_by_id(widget_id)

            # Validate
            if (widget):

                # Add
                results.append(widget)

        # Done!
        return results


    # Get the active widget
    def get_active_widget(self):

        # Stack itself must have focus
        if ( 1 or self.is_focused() ):

            # Check each widget
            for widget in self.widgets:

                # Is this the most recently selected widget?  No cursor for widget stack, so check attribute...
                if ( widget.get_id() == self.active_widget_id ):

                    return widget


            # No widget has focus
            return None

        # No focus at all
        else:

            return None


    # Determine which widget in the stack has the focus by its widget ID (attribute)
    def set_active_widget_by_id(self, widget_id):

        # Track active widget id
        self.active_widget_id = widget_id


        # Loop through widgets, blurring all but active
        for widget in self.widgets:

            # Check widget id
            if ( widget.get_id() == widget_id ):

                # Mark as active via attribute
                widget.set_attribute("focused", "1")

                # Make active
                widget.focus()

            # Any other widget must be inactive
            else:

                # Mark as inactive via attribute
                widget.set_attribute("focused", "0")

                # Assume inactive
                widget.blur()


    def handle_user_input(self, control_center, universe):

        # Events created based on user input
        results = EventQueue()


        # Does this stack even care about user input?
        if (self.uses_focus):

            # Try to find an active widget
            widget = self.get_active_widget()

            # Validate
            if (widget):

                # Do both stack and widget have focus?
                if ( ( self.is_focused() ) and ( widget.is_focused() ) ):

                    # Process widget (with input)
                    results.append(
                        widget.handle_user_input(control_center, universe)
                    )


        # Return events
        return results



    # Process stack
    def process(self, control_center, universe):#user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        #result = {}


        # Process widgets
        for widget in self.widgets:

            # Process widget (no input)
            results.append(
                widget.process(control_center, universe)#[], [], network_controller, universe, session, save_controller)
            )


        # Return events
        return results


        #return result


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Default render point
        (rx, ry) = (
            sx + self.get_x() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width(),
            max( self.min_height, self.get_render_height(text_renderer) )
        )

        # Adjust for vertical centering?
        if (self.valign == "center"):

            ry = int(SCREEN_HEIGHT / 2) - int(self.report_widget_height(text_renderer) / 2)


        # Use our own alpha value
        alpha = self.alpha_controller.get_interval()
        #print "**Stack alpha = ", alpha


        # Place a border around the entire stack?
        if (self.render_border):

            self.__std_render_border__(sx + self.get_x(), sy + self.get_y(), width, height, window_controller)


        # Widget rendering point
        (wx, wy) = (
            rx + self.get_padding_left(),
            ry + self.get_padding_top()
        )

        # Track vertical offset as we move down the Stack
        dy = 0 + self.get_padding_top()

        # Loop widgets
        for widget in self.widgets:

            # Visibility check
            if ( (widget.display == "constant") or ( widget.display == "on-focus" and self.is_focused() ) or (widget.display == "on-focus:linger" and ( self.is_focused() or widget.linger() )) or (widget.display == "off-focus" and ( not self.is_focused() )) ):

                # Render widget
                widget.draw(rx, ry + dy, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


            # Increment rendering position by full box height, plus any padding between widgets in the stack
            dy += widget.get_box_height(text_renderer) + self.pane_padding


        #window_controller.get_geometry_controller().draw_rect(rx, ry, self.get_width(), self.report_widget_height(text_renderer), (25, 225, 25, 0.25))
