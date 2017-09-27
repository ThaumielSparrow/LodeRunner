#from glfunctions import draw_rect, draw_rounded_rect, draw_rounded_rect_with_gradient

from code.ui.common import UIWidget

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, xml_encode, xml_decode, set_alpha_for_rgb, evaluate_spatial_expression

from code.constants.common import INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_ACTIVATE, SLIDE_MENU_ITEM_HEIGHT, SLIDE_MENU_ITEM_PADDING, SLIDE_MENU_INDENT_AMOUNT, SCREEN_WIDTH

from code.constants.sound import *


class HMenu(UIWidget):

    def __init__(self):#, w = 0, on_wrap_up = None, on_wrap_down = None, on_selection_change = None, on_selection_activate = None):

        # Set up basic window properties and features
        UIWidget.__init__(self, selector = "hmenu")


        # Menu widgets, displayed in a horizontal list with equal widths
        self.widgets = []

        # current selection
        self.cursor = 0


        # Menu currently active?
        self.active = False


        # What to do if the user goes above/below the darned thing?
        self.on_wrap_up = None
        self.on_wrap_down = None

        # What to do if the selection changes?
        self.on_change = None


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        if ( "on-change" in options ):
            self.on_change = options["on-change"]

        if ( "on-wrap-up" in options ):
            self.on_wrap_up = options["on-wrap-up"]

        if ( "on-wrap-down" in options ):
            self.on_wrap_down = options["on-wrap-down"]


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


    # Save HMenu state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Add in a few state details specific to this HMenu
        details_node = root.add_node(
            XMLNode("hmenu")
        )

        # Save cursor position
        details_node.set_attributes({
            "cursor.x": self.cursor
        })


        # Add in state of any child widget
        descendants_node = details_node.add_node(
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


    # Load HMenu state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Grab details specific to this HMenu
        details_node = node.find_node_by_tag("hmenu")

        # Validate
        if (details_node):

            # Restore cursor
            self.set_cursor( int( details_node.get_attribute("cursor.x") ) )


            # Check for descendant state data
            descendants_node = details_node.find_node_by_tag("descendants")

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
            <self has-focus = '%d'>
                <cursor x = '%d' />
            </self>
        """ % (self.has_focus, self.cursor)

        return xml


    def load_state_from_xml(self, xml):

        # Generic node
        node = XMLParser().create_node_from_xml(xml)

        # Load HMenu data
        ref_self = node.get_first_node_by_tag("self")

        if (ref_self):

            # Did we have focus?
            self.has_focus = ( int(ref_self.get_attribute("has-focus")) == 1 )


            # Load the cursor data
            ref_cursor = ref_self.get_first_node_by_tag("cursor")

            if (ref_cursor):

                self.set_cursor( int( ref_cursor.get_attribute("x") ) )


    """ Event callbacks """
    # On birth, we should place the cursor at 0
    def handle_birth(self):

        # Track events
        results = EventQueue()


        # Append results of moving cursor by "0"
        results.append(
            self.move_cursor(0) # Wake-up
        )


        # Check child widgets
        for widget in self.widgets:

            results.append(
                widget.handle_birth()
            )


        # Return events
        return results


    # The HMenu widget uses a custom on focus callback.
    # This widget only gives focus to the active selection, choosing to blur any other option.
    def on_focus(self):

        # Get child widgets
        widgets = self.get_child_widgets()

        # Loop child widgets
        for i in range( 0, len(widgets) ):

            # Active widget?
            if (i == self.cursor):

                # We have to update the bloodline for each widget
                widgets[i].css({
                    "bloodline": self.get_bloodline()
                }).focus()


            # No; blur it...
            else:

                # We have to update the bloodline for each widget
                widgets[i].css({
                    "bloodline": self.get_bloodline()
                }).blur()



    # Note that we use the inherited on blur callback here.  Everything gets blurred equally.


    # On resize, we should set each child widget's max width to this widget's width...
    def on_resize(self, text_renderer = None):

        # Cascade
        for widget in self.widgets:

            widget.configure({
                "max-width": self.get_width() - ( self.get_padding_left() + self.get_padding_right() ),
            })

            if (text_renderer):

                widget.configure({
                    "max-height": self.report_widget_height(text_renderer)
                })


    def count(self):

        return len(self.widgets)


    # Because the width of the HMenu does not depend on text in any way,
    # I am defining this convenience function to passes a null for the report param.
    def xget_width(self):

        return self.report_widget_width(text_renderer = None)


    def report_widget_width(self, text_renderer):

        return ( self.width - ( self.get_padding_left() + self.get_padding_right() ) )


    def report_widget_height(self, text_renderer):

        if ( len(self.widgets) > 0 ):

            # Use the box height for each widget, as this HMenu contains them in their entirety
            return max( widget.get_box_height(text_renderer) for widget in self.widgets )

        # No widgets, no height
        else:

            return 0

        #return text_renderer.font_height + (2 * self.padding)


    def add_widget(self, widget):#name, title):

        self.widgets.append(widget)

        # Update width for each widget
        for widget in self.widgets:

            widget.configure({
                "bloodline": self.get_bloodline(),
                "width": "%d%%" % int( 100 * float( 1.0 / len(self.widgets) ) ) # Equal, percentage-based width for each widget
            })


        return self.widgets[-1]


    # Convenience function
    def add_widget_with_id(self, widget, widget_id):

        # Set widget's id
        widget.set_id(widget_id)

        # Add widget
        self.add_widget(widget)


    # Populate with widget containers
    def populate_from_collection(self, collection, control_center, universe):

        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Validate we have items to add
        if ( len(collection) > 0 ):

            #"max-width": self.get_width() - ( self.get_padding_left() + self.get_padding_right() ),

            # Width per item in the hmenu
            width_per = int( ( self.get_width() - ( self.get_padding_left() + self.get_padding_right() ) ) / len(collection) )

            #print self.get_padding_left()
            #print self.get_padding_right()
            #print 5/0


            # First add the containers.  Do this in its own stage to finalize the width of each individual container
            for node in collection:

                node.set_attributes({
                    "max-width": width_per
                })

                # Create the top-level node (the widget container)
                container = widget_dispatcher.convert_node_to_widget(
                    node,
                    control_center,
                    universe
                )

                self.add_widget_with_id(
                    container.configure(
                        node.get_attributes()
                    ).set_attributes({
                        "rel": node.get_attribute("rel") # Track the name of the node we found so that we can revisit it to present GridMenu pages for each tab option
                    }),
                    node.get_attribute("rel")
                )


            """
            # After adding the empty containers to the navbar, let's loop through the nodes one more time
            # to fetch the contents and add them to the containers (which now have a final width set)...
            for node in collection:

                # Find the widget by id
                container = self.get_widget_by_id( node.get_attribute("rel") )

                # Validate
                if (container):

                    # Populate containre widget
                    container.populate_from_collection(
                        node.get_nodes_by_tag("*"),
                        control_center,
                        universe
                    )
            """


    def get_item_by_name(self, name):

        for item in self.items:

            if (item.name == name):
                return item

        return None


    def get_cursor(self):

        return self.cursor


    def set_cursor(self, value):

        # Place cursor
        self.cursor = value


        # Remove active state from all widgets
        for widget in self.widgets:

            # No state
            widget.css({
                "state": "",
                "class": ""
            }).blur()

        # Now add active status to the selected widget
        self.widgets[self.cursor].css({
            "state": "active",
            "class": "cursor"
        }).focus()

        log( "**cursor moved" )


        """
        # Check for onchange callback
        if (self.on_change):

            results.add(
                action = self.on_change
            )
        """


    def move_cursor(self, amount):

        # Events that result from cursor movement (on-change, etc.)
        results = EventQueue()


        # Calculate new cursor position
        target = self.cursor + amount

        # Wraparound
        if ( target < 0 ):

            target += self.count()

        elif ( target >= self.count() ):

            target -= self.count()


        # on-change event?
        if (self.on_change):

            results.add(
                action = self.on_change,
                params = {
                    "widget": self
                }
            )


        # Set cursor
        self.set_cursor(target)


        # Return events
        return results


    # Activate an item (toggle submenu, return name)
    def activate_selection(self):

        item = self.items[self.cursor]

        return item.name


    def deactivate(self):

        log( "** Let's use blur instead, I think" )
        log( 5/0 )
        self.active = False


    def get_value(self):

        return "root.my-universe"
        return self.items[self.cursor].name


    # Get the active cursor selection
    def get_active_widget(self):

        if ( len(self.widgets) > 0 ):

            return self.widgets[self.cursor]

        else:

            return None


    # Get a widget by its id
    def get_widget_by_id(self, widget_id):

        # Check all
        for widget in self.widgets:

            # id comparison
            if ( widget.get_id() == widget_id ):

                return widget


        # Couldn't find it
        return None


    def set_value_by_name(self, name):

        for i in range(0, len(self.items)):

            if (self.items[i].name == name):

                self.set_cursor(i)


    def handle_user_input(self, control_center, universe):

        # Events resulting from user input
        results = EventQueue()


        # If this widget has been poked, "move" the cursor (by 0) to trigger the on-change event.
        if (self.poked):

            # Wake up
            results.append(
                self.move_cursor(0)
            )

            # Flag off
            self.poked = False

        if ( 0 and self.poked ):

            # Handle inbox
            event = self.inbox.fetch()

            # Loop all messages
            while (event):

                # Check action
                (action, params) = (
                    event.get_action(),
                    event.get_params()
                )


                # Trigger a callback?
                if (action == "wake"):

                    # Wake up
                    results.append(
                        self.move_cursor(0)
                    )


                # Next!
                event = self.inbox.fetch()


            # Flag off
            self.poked = False


        # Fetch gameplay input (used as user input) from input controller
        user_input = control_center.get_input_controller().get_gameplay_input()


        if ( self.is_focused() ):

            if (INPUT_SELECTION_LEFT in user_input):

                results.append(
                    self.move_cursor(-1)
                )

                # Tick sound effect
                control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

            elif (INPUT_SELECTION_RIGHT in user_input):

                results.append(
                    self.move_cursor(1)
                )

                # Tick sound effect
                control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

            elif (INPUT_SELECTION_DOWN in user_input):

                if (self.on_wrap_down):

                    results.add(
                        action = self.on_wrap_down,
                        params = {
                            "widget": self
                        }
                    )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

            elif ( (INPUT_SELECTION_UP in user_input) ):

                if (self.on_wrap_up):

                    results.add(
                        action = self.on_wrap_up,
                        params = {
                            "widget": self
                        }
                    )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

            elif (INPUT_SELECTION_ACTIVATE in user_input):

                # Get active widget
                widget = self.get_active_widget()

                # Validate
                if (widget):

                    # Check widget on_select results
                    widget_results = widget.on_select()

                    log( "**results", widget_results )

                    # Found results?
                    if (widget_results != None):

                        results.append(
                            widget_results
                        )

                        # Selection sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_SELECT)


        # Return events
        return results


    # Process user input
    def process(self, control_center, universe):#, user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Process each child widget
        for widget in self.widgets:

            results.append(
                widget.process(control_center, universe)
            )


        # Return events
        return results


    # Draw the darned thing
    #def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, alpha, window_controller = None, f_draw_worldmap = None):
    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Render position
        (rx, ry) = (
            sx + self.get_x() + 0*self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + 0*self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width(),
            self.get_render_height(text_renderer)
        )

        alpha_factor = self.get_background_alpha()


        # Use our own alpha value
        alpha = self.alpha_controller.get_interval()

        # Render a backdrop
        window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
            rx,
            ry - 0*self.get_padding_top(),
            width,
            height,
            background1 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_start() ),
            background2 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_end() ),
            border = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ),
            border_size = self.get_border_size(),
            shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ),
            shadow_size = self.get_shadow_size(),
            gradient_direction = self.get_gradient_direction()
        )
        """
        window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(
            sx,
            sy + self.get_margin_top(),
            self.width,
            self.get_render_height(text_renderer),
            set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_start() ),
            set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_end() )
        )
        """


        # Render point for the contents
        (rx, ry) = (
            rx + self.get_padding_left(),
            ry + self.get_padding_top()
        )

        #i = 1
        for widget in self.widgets:

            widget.draw(rx, ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

            #window_controller.get_geometry_controller().draw_rect(rx, ry, width_per, 20, (20 + i * 20, 40 + i * 40, 60 + i * 60, 0.25))
            #window_controller.get_geometry_controller().draw_rect(rx, ry + 20, width_per, 5, (225, 25, 25, 0.5))
            #i += 1

            rx += widget.get_width()#width_per
            #print "  **width per:  ", widget.get_width()
