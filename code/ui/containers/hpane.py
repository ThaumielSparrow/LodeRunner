import sys

from code.ui.common import UIWidget

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, logn, xml_encode, xml_decode, set_alpha_for_rgb

from code.constants.common import DIR_LEFT, DIR_RIGHT, SCREEN_WIDTH, SCREEN_HEIGHT

class HPane(UIWidget):

    def __init__(self):#, width = 0, item1 = None, item2 = None, width1 = 0.5, width2 = 0.5, handedness = DIR_LEFT, center_vertically = False):

        UIWidget.__init__(self, selector = "hpane")


        self.state_changed = False

        # Pane percentages
        self.width1 = 0.5
        self.width2 = 0.5

        self.pane_padding = 25 # hard-coded


        # Horizontal alignment
        self.halign = "left" # left, center, right

        # Vertical alignment
        self.valign = "top" # top, center, bottom


        # Shrinkwrap setting
        self.shrinkwrap = False


        self.item1 = None
        self.item2 = None


        # Which pane will have user input?  Right now, I only support one side having focus; the other side is strictly informational...
        self.handedness = DIR_LEFT # default

        # Just for record-keeping; we don't actually use this.
        self.cursor = None


        # Render a divider between the panes?
        self.render_divider = False


        # Will this HMenu center vertically?
        self.center_vertically = False


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Widget members
        if ( "item1" in options ):

            self.item1 = options["item1"]

            # Set parent on item1 to this HPane
            self.item1.set_parent(self)

            #self.item1.configure({
            #    "max-width": int( (self.get_width() - self.pane_padding) * self.width1 )
            #})
            #print "**calc max width @ ", int( (self.get_width() - self.pane_padding) * self.width1 )

        if ( "item2" in options ):

            self.item2 = options["item2"]

            # Set parent on item2 to this HPane
            self.item2.set_parent(self)

            #self.item2.configure({
            #    "max-width": int( (self.get_width() - self.pane_padding) * self.width2 )
            #})
            #print "**calc max width @ ", int( (self.get_width() - self.pane_padding) * self.width2 )


        # Process left/right percentage width first
        if ( "width-left" in options ):

            self.width1 = float( options["width-left"] )

        if ( "width-right" in options ):

            self.width2 = float( options["width-right"] )


        if ( "handedness" in options ):

            if ( options["handedness"] == "left" ):
                self.handedness = DIR_LEFT

            elif ( options["handedness"] == "right" ):
                self.handedness = DIR_RIGHT

            else:
                self.handedness = int( options["handedness"] )


        if ( "render-divider" in options ):
            self.render_divider = ( int( options["render-divider"] ) == 1 )


        if ( "center-vertically" in options ):
            self.center_vertically = ( int ( options["center-vertically"] ) == 1 )

        if ( "halign" in options ):
            self.halign = options["halign"]

        if ( "valign" in options ):
            self.valign = options["valign"]

        if ( "shrinkwrap" in options ):
            self.shrinkwrap = ( int( options["shrinkwrap"] ) == 1 )



        """
        # Update item dimensions (in case we changed a related setting)
        if (self.item1):

            self.item1.configure({
                "max-width": int( (self.get_width() - self.pane_padding) * self.width1 )
            })

        if (self.item2):

            self.item2.configure({
                "max-width": int( (self.get_width() - self.pane_padding) * self.width2 )
            })
        """


        # Account for any resizing
        self.on_resize()


        # For chaining
        return self


    # Configure the alpha controller, then cascade
    def configure_alpha_controller(self, options):

        # Standard alpha configuration
        UIWidget.configure_alpha_controller(self, options)


        # Cascade to left pane
        if (self.item1):

            # Cascade
            self.item1.configure_alpha_controller(options)

        # Cascade to right pane
        if (self.item2):

            # Cascade
            self.item2.configure_alpha_controller(options)


    # Save HPane state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Add in a few state details specific to this HPane
        details_node = root.add_node(
            XMLNode("hpane")
        )

        # Save handedness
        details_node.set_attributes({
            "handedness": self.handedness
        })


        # Add in state of any child item
        descendants_node = XMLNode("descendants")


        # Check left pane
        if (self.item1):

            # Save left pane state
            item_node = descendants_node.add_node(
                XMLNode("item1")
            )

            # Track the left pane's state node within
            item_node.add_node(
                self.item1.save_state()
            )

        # Check right pane
        if (self.item2):

            # Save right pane state
            item_node = descendants_node.add_node(
                XMLNode("item2")
            )

            # Track state node within
            item_node.add_node(
                self.item2.save_state()
            )


        # Return node
        return root


    # Load HPane state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Grab details specific to this RowMenu
        details_node = node.find_node_by_tag("hpane")

        # Validate
        if (details_node):

            # Restore handedness
            self.handedness = int( details_node.get_attribute("handedness") )


            # Check for descendant state data
            descendants_node = details_node.find_node_by_tag("descendants")

            # Validate
            if (descendants_node):

                # Check for item 1 data
                item_node = descendants_node.find_node_by_tag("item1")

                # Validate
                if (item_node):

                    # Do we even have a left pane widget?
                    if (self.item1):

                        # Restore item1's state
                        self.item1.load_state(
                            item_node.find_first_node_by_tag("widget")
                        )


                # Check for item 2 data
                item_node = descendants_node.find_node_by_tag("item2")

                # Validate
                if (item_node):

                    # Do we even have a right pane widget?
                    if (self.item2):

                        # Restore item2's state
                        self.item2.load_state(
                            item_node.find_node_by_tag("widget")
                        )


    # Get child widgets
    def get_child_widgets(self):

        # Tracking
        results = []


        # Do we have a left pane?
        if (self.item1):

            # Add
            results.append(self.item1)

        # Do we have a right pane?
        if (self.item2):

            # Add
            results.append(self.item2)


        # Return all widgets
        return results


    def save_state_as_xml(self):

        xml = """
            <self handedness = '%d' slide-interval = '%d' slide-interval-target = '%d'>
                <item index = '1'>
                    #ITEM1XML
                </item>
                <item index = '2'>
                    #ITEM2XML
                </item>
            </self>
        """ % (self.handedness, self.slide_interval, self.slide_interval_target)

        if (self.item1):
            xml = xml.replace("#ITEM1XML", self.item1.save_state_as_xml())

        else:
            xml = xml.replace("#ITEM1XML", "")


        if (self.item2):
            xml = xml.replace("#ITEM2XML", self.item2.save_state_as_xml())

        else:
            xml = xml.replace("#ITEM2XML", "")


        return xml

    def load_state_from_xml(self, xml):

        # Generic node
        node = XMLParser().create_node_from_xml(xml)

        # Load the hpane-specific data
        ref_self = node.get_first_node_by_tag("self")

        if (ref_self):

            self.handedness = int( ref_self.get_attribute("handedness") )

            self.slide_interval = int( ref_self.get_attribute("slide-interval") )
            self.slide_interval_target = int( ref_self.get_attribute("slide-interval-target") )


            # Try to get item1 / item2
            if (self.item1):

                ref_item = ref_self.get_first_node_by_tag("item", {"index": "1"})

                if (ref_item):
                    #self.item1.load_state_from_xml( ref_item.compile_xml_string() )
                    self.item1.load_state_from_xml( ref_item.compile_inner_xml_string() )

            if (self.item2):

                ref_item = ref_self.get_first_node_by_tag("item", {"index": "2"})

                if (ref_item):
                    self.item2.load_state_from_xml( ref_item.compile_inner_xml_string() )


    """ Event callbacks """
    # On birth, we should check each pane
    def handle_birth(self):

        # Track events
        results = EventQueue()

        if (self.item1):

            results.append(
                self.item1.handle_birth()
            )

        if (self.item2):

            results.append(
                self.item2.handle_birth()
            )


        # Return events
        return results


    # On resize, ths HPane should update the max width of its panes
    def on_resize(self, text_renderer = None):

        # Check left pane
        if (self.item1):

            self.item1.configure({
                "max-width": int( (self.get_width() - self.pane_padding) * self.width1 )
            })

            if (text_renderer):

                self.item1.configure({
                    "max-height": self.report_widget_height(text_renderer)
                })

            self.item1.on_resize(text_renderer)

        # Check right pane
        if (self.item2):

            self.item2.configure({
                "max-width": int( (self.get_width() - self.pane_padding) * self.width2 )
            })

            if (text_renderer):

                self.item2.configure({
                    "max-height": self.report_widget_height(text_renderer)
                })

            self.item2.on_resize(text_renderer)


    # Get up-to-date height calculations on each item, take the max,
    # and then apply that specific height to both panes
    def update_height(self, text_renderer):

        (height1, height2) = (0, 0)

        if (self.item1):
            height1 = self.item1.report_widget_height(text_renderer)

        if (self.item2):
            height2 = self.item2.report_widget_height(text_renderer)

        self.height = max(height1, height2)


    def update_height_and_shrinkwrap(self, text_renderer):

        self.update_height(text_renderer)

        if (self.item1):
            self.item1.height = self.height

        if (self.item2):
            self.item2.height = self.height


    # Raw widget height
    def report_widget_height(self, text_renderer):

        # loop children
        try:
            return max( widget.get_box_height(text_renderer) for widget in self.get_child_widgets() )

        # Empty list exception
        except:
            return 0


    def get_cursor(self):

        if (self.handedness == DIR_LEFT):

            return self.item1.get_cursor()

        elif (self.handedness == DIR_RIGHT):

            return self.item2.get_cursor()


    def set_cursor(self, cursor):

        if (self.handedness == DIR_LEFT):

            self.item1.set_cursor(cursor)

        elif (self.handedness == DIR_RIGHT):

            self.item2.set_cursor(cursor)


    # Alias
    def translate(self, h):
        self.translate_environment_variables(h)

    # Translate a given hash of environment variables
    def translate_environment_variables(self, h):

        # Loop potential children
        for widget in [self.item1, self.item2]:

            # Validate widget
            if (widget):

                # Do not descend into new namespaces
                if ( widget.get_namespace() == None ):

                    #print 5/0
                    # Translate child widget
                    widget.translate_environment_variables(h)


        # This widget only contains other widgets; it will not translate
        # anything of its own self.


    # Find a widget within this HPane widget by a given id
    def find_widget_by_id(self, widget_id):

        # Left item exists?
        if (self.item1):

            # Matches?
            if ( self.item1.get_id() == widget_id ):

                # Return immediately
                return self.item1

            # Try potential children
            else:

                # Scan
                widget = self.item1.find_widget_by_id(widget_id)

                # Matched?
                if (widget):
                    return widget

        # Right item exists?
        if (self.item2):

            # Matches?
            if ( self.item2.get_id() == widget_id ):

                # Return immediately
                return self.item2

            # Try potential children
            else:

                # Scan
                widget = self.item2.find_widget_by_id(widget_id)

                # Matched?
                if (widget):
                    return widget


        # Neither side matches the given widget id
        return None


    def get_active_item(self):

        if (self.handedness == DIR_LEFT):

            return self.item1

        elif (self.handedness == DIR_RIGHT):

            return self.item2

        else:

            return None


    def set_handedness(self, value):

        self.handedness = value

        if (self.handedness == DIR_LEFT):

            if (self.item1):
                self.item1.focus()

            if (self.item2):
                self.item2.blur()

        elif (self.handedness == DIR_RIGHT):

            if (self.item1):
                self.item1.blur()

            if (self.item2):
                self.item2.focus()


    def handle_user_input(self, control_center, universe):

        # Events that arise from user input
        results = EventQueue()


        if (self.item1):

            if (self.handedness == DIR_LEFT):

                results.append(
                    self.item1.handle_user_input(control_center, universe)
                )


        if (self.item2):

            if (self.handedness == DIR_RIGHT):

                results.append(
                    self.item2.handle_user_input(control_center, universe)
                )


        # Return events
        return results


    def process(self, control_center, universe):#user_input, raw_keyboard_input, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Process left pane
        if (self.item1):

            results.append(
                self.item1.process(control_center, universe)
            )

        # Process right pane
        if (self.item2):

            results.append(
                self.item2.process(control_center, universe)
            )


        # Return events
        return results


    #def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, alpha, window_controller = None, f_draw_worldmap = None):
    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Account for sliding...
        #sx += int( self.hslide_controller.get_interval() )
        #sy += int( self.vslide_controller.get_interval() )


        # Default render point
        #(rx, ry) = (
        #    sx,
        #    sy + self.get_y()
        #)
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width(),
            self.get_height(text_renderer)
        )

        # If we center vertically, then we'll overwrite ry...
        if (self.center_vertically):

            ry = int(SCREEN_HEIGHT / 2) - int(height / 2)


        # Default align
        if (self.halign == "left"):
            pass

        # Center horizontally?
        elif (self.halign == "center"):

            # Offset by 50%
            rx -= int(width / 2)

        # Align right?
        elif (self.halign == "right"):

            # Offset by 100%
            rx -= width


        # Center vertically?
        if (self.valign == "center"):

            # Calculate height
            #height = self.report_widget_height(text_renderer)

            #print "**height = ", height

            # Assume
            h = height

            # Shrinkwrap?
            if (self.shrinkwrap):

                # Base alignment on used height
                h = self.get_render_height(text_renderer)

            # Align
            ry -= int(h / 2)

        # Align to the bottom?
        elif (self.valign == "bottom"):

            # Assume
            h = height

            # Shrinkwrap?
            if (self.shrinkwrap):

                # Base alignment on used height
                h = self.get_render_height(text_renderer)

            # Align
            ry -= h


        # Use widget's very own alpha data
        alpha = self.alpha_controller.get_interval()


        # Place a border around the entire HPane?
        if (self.render_border):

            self.__std_render_border__(rx, ry, width, height, window_controller)


        # Render a divider between the panes?
        if (self.render_divider):

            # Divider padding (top and bottom)
            padding = 10

            # Ultimate divider length
            length = int( (height - (2 * padding)) / 2 )

            log2( "grad-end", self.get_gradient_end() )

            window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(
                sx + int( self.get_width() / 2 ) - 1, sy + padding, 2, int(length / 2), self.get_gradient_start(), self.get_gradient_end()
            )

            window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(
                sx + int( self.get_width() / 2 ) - 1, sy + padding + int(length / 2), 2, int(length / 2), self.get_gradient_end(), self.get_gradient_start()
            )

            window_controller.get_geometry_controller().draw_rect(
                5 + sx + int( self.get_width() / 2 ) - 1, sy + padding, 2, length, self.get_gradient_end()
            )


        if (self.handedness == DIR_LEFT):

            if (self.item2):
                self.item2.draw(rx + (self.get_width() - self.item2.get_width()), ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

                #window_controller.get_geometry_controller().draw_rect(
                #    rx + (self.get_width() - self.item2.get_width()) + 0*self.pane_padding, ry, self.item2.get_width(), max(25, self.item2.get_height(text_renderer)), (25, 225, 25, 0.15)
                #)

                #text_renderer.render_with_wrap( "%s, %s, %s" % (self.get_width(), self.width, self.max_width), rx + (self.get_width() - self.item2.get_width()), ry, (225, 225, 25, 0.5))

            if (self.item1):
                self.item1.draw(rx, ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

                #window_controller.get_geometry_controller().draw_rect(
                #    rx, ry, self.item1.get_width(), self.item1.get_height(text_renderer), (225, 225, 25, 0.15)
                #)

        else:

            if (self.item1):
                self.item1.draw(rx, ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

            if (self.item2):
                self.item2.draw(rx + (self.get_width() - self.item2.get_width()), ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)




        #if (self.css_class in ("bordered", "debug2")):
        #    text_renderer.render("%s, %s" % (self.alpha_controller.get_interval(), self.alpha_controller.get_target()), rx, ry + text_renderer.font_height, (175, 175, 225, 0.75))
