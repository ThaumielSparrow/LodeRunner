import sys

from code.ui.common import UIWidget

from code.tools.eventqueue import EventQueue

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_PROMPT_WIDTH, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_HOME, INPUT_SELECTION_END, INPUT_SELECTION_PAGEUP, INPUT_SELECTION_PAGEDOWN, INPUT_SELECTION_ACTIVATE, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, DATE_WIDTH, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIALOGUE_PANEL_WIDTH, DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE, LITERAL_POSITION_TRANSLATIONS, TOOLTIP_MIN_PADDING_X, TOOLTIP_MIN_PADDING_Y
from code.constants.common import STENCIL_MODE_NONE, STENCIL_MODE_PAINT, STENCIL_MODE_ERASE, STENCIL_MODE_PAINTED_ONLY, STENCIL_MODE_UNPAINTED_ONLY

from code.constants.sound import *

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import evaluate_spatial_expression, intersect, intersect_y, offset_rect, log, log2, logn, xml_encode, xml_decode, set_alpha_for_rgb, coalesce

class Group(UIWidget):

    def __init__(self):

        UIWidget.__init__(self, selector = "group")


        # Track widgets in this group
        self.widgets = []



        # Widgets per row
        self.per_row = 1

        # Column padding (if more than one widget exists per row)
        self.column_padding = 0


        # Should every widget in the group render at the same height?
        self.homogenize = False

        # Determine the group's border / positioning / etc. based on the number of items actually in the group? (e.g. true centering if all columns are not filled)
        self.fit_width = False


        # Horizontal alignment
        self.halign = "left" # left, center, or right

        # For non-scrolling RowMenus, we might want to align the final item
        # at the bottom of the RowMenu
        self.valign = None


        # We may eventually cache certain metrics
        self.cached_metrics = {}


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Group-specific configuration options
        if ( "per-row" in options ):
            self.per_row = int( options["per-row"] )

        if ( "column-padding" in options ):
            self.column_padding = int( options["column-padding"] )

        if ( "homogenize" in options ):
            self.homogenize = ( int( options["homogenize"] ) == 1 )

        if ( "fit-width" in options ):
            self.fit_width = ( int( options["fit-width"] ) == 1 )

        if ( "disabled" in options ):
            self.disabled = ( int( options["disabled"] ) == 1 )

        if ( "halign" in options ):
            self.halign = options["halign"]

        if ( "valign" in options ):
            self.valign = options["valign"]


        # For chaining
        return self


    # Configure the alpha controller, then cascade
    def configure_alpha_controller(self, options):

        # Standard alpha configuration
        UIWidget.configure_alpha_controller(self, options)

        # Cascade to child widgets
        for widget in self.widgets:

            # Cascade
            widget.configure_alpha_controller(options)


    # Save Group state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Create a node to track each widget in this group
        widgets_node = root.add_node(
            XMLNode("widgets")
        )

        # Save state of each item's widget
        for i in range( 0, len(self.widgets) ):

            # Add child state
            widgets_node.add_node(
                self.widgets[i].save_state()
            )


        # Return node
        return root


    # Load Group state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Check for widget states
        widgets_node = node.get_first_node_by_tag("widgets")

        # Validate
        if (widgets_node):

            # Set state for each widget.
            # The widget can be of any type (label, box, hpane, whatever!), so we just grab every tag.
            widget_node_collection = widgets_node.get_nodes_by_tag("*")

            # Loop in sequence
            for i in range( 0, len(self.widgets) ):

                # Sanity
                if ( i < len(widget_node_collection) ):

                    # Restore state
                    self.widgets[i].load_state(
                        widget_node_collection[i]
                    )


    # Get child widgets
    def get_child_widgets(self):

        # Return all widgets
        return self.widgets


    """ Event callbacks """
    # On birth, we should blur each item widget?
    def handle_birth(self):

        # Track events
        results = EventQueue()


        for widget in self.widgets:

            widget.blur()

            results.append(
                widget.handle_birth()
            )




        """
        # Check child widgets
        for widget in self.widgets:

            results.append(
                widget.handle_birth()
            )
        """


        # Return events
        return results

    # A RowMenu Group doesn't handle focus logic for its child widgets.
    def on_focus(self):

        return


    # A RowMenu Group doesn't handle blur logic for its child widgets.
    def on_blur(self):

        return


    # On resize, we need to forward new size data to all child items (within the wrapped item things)
    def on_resize(self, text_renderer = None):

        # Cascade
        for i in range( 0, len(self.widgets) ):

            # Convenience
            widget = self.widgets[i]

            widget.configure({
                "max-width": self.get_cell_width()
            })


            widget.configure({
                "max-height": self.report_widget_height(text_renderer),
                "style-height": 0 # Assume no homogenization, no predefined style height
            })


        for widget in self.widgets:

            widget.on_resize(text_renderer)


        if ( self.homogenize ):

            for i in range( 0, len(self.widgets) ):

                # Which row does this widget belong to?
                row = int(i / self.per_row)


                # Assume
                homogenized_height = 0

                # Calculate tallest widget in this row
                try:
                    homogenized_height = max( widget.report_widget_height(text_renderer) for widget in self.get_widgets_in_row(row) )

                # Empty list returned to max()?
                except:
                    pass

                homogenized_height = max( widget.report_widget_height(text_renderer) for widget in self.get_widgets_in_row(row) )

                #item.get_widget().configure({
                #    "style-height": self.get_max_render_height_in_group(text_renderer)
                #})
                self.widgets[i].configure({
                    "style-height": homogenized_height
                })

                #print "Homogenization max for [row %d, item %d] = %d" % (row, i, homogenized_height)


    def add(self, widget):

        self.widgets.append(widget)

        # Set parent on widget to this group
        widget.set_parent(self)

        # For chaining
        return self.widgets[-1]


    def count(self):

        return len(self.widgets)


    def count_rows(self):

        return int( ( len(self.widgets) + (self.per_row - 1) ) / self.per_row )


    def get_cell_width(self):

        # Available width...
        available_width = self.get_width() - ( (self.per_row - 1) * self.column_padding )

        # Evenly distributd among all columns...
        return int(available_width / self.per_row)


    def get_group_width(self):

        return self.get_width()


    # A group must sum the height required by all of the rows (accounting for potential column use)
    def report_widget_height(self, text_renderer):

        metric = self.get_cached_metric("reported-widget-height")

        if (metric != None):

            return metric

        else:

            metric = 0

            # Go through each row
            for i in range( 0, self.count_rows() ):

                # Find the highest widget container in this row
                try:
                    metric += max( widget.get_box_height(text_renderer) for widget in self.get_widgets_in_row(i) )

                # Empty row (?)
                except:
                    pass

            # Cache metric
            self.cache_metric("reported-widget-height", metric)

            # Return
            return metric


    # Alias
    def translate(self, h):
        self.translate_environment_variables(h)

    # Translate widgets within this RowMenu using a given hash
    def translate_environment_variables(self, h):

        # Loop each widget in this group
        for widget in self.widgets:

            # Do not descend into new namespaces
            if ( widget.get_namespace() == None ):

                # Forward translations
                widget.translate_environment_variables(h)

        
    # Which row does a given item land on?
    def get_row_by_widget_index(self, index):

        return int(index / self.per_row)


    # Get all of the widgets in a given row
    def get_widgets_in_row(self, index):

        # Calculate range
        (a, b) = (
            index * self.per_row,
            (index * self.per_row) + self.per_row
        )

        # Return matching widgets
        return self.widgets[a:b]


    # How many columns does a given row contain?
    def count_columns_in_row(self, row):

        # Assume full row
        (a, b) = (
            row * self.per_row,
            (row * self.per_row) + self.per_row
        )

        # But the last row may not reach the end...
        if (b > len(self.widgets)):

            b = len(self.widgets)

        # Calculate
        return (b - a)


    # Which column does an item occupy within a given row?
    def get_column_by_widget_index(self, index):

        # Calculate row
        #row = self.get_row_by_widget_index
        return (index % self.per_row)


    # Get the tallest item on a given row...
    def get_row_height(self, row, text_renderer):

        # Which items apply?
        (a, b) = (
            (row * self.per_row),
            (row * self.per_row) + self.per_row
        )

        # Clamp bounds if necessary.
        # Note that we clamp based on desired parameters for a range() statement, so it's inclusive.
        if ( b > len(self.widgets) ):

            # Clamp
            b = len(self.widgets)


        # Get max of said items...
        try:
            return max( self.widgets[i].get_box_height(text_renderer) for i in range(a, b) )

        # 0 item list?
        except:

            logn( "rowmenu group error", sys.exc_info() )
            logn( "rowmenu group error", "Aborting:  0 items in group!" )
            sys.exit()

            return 0


    def get_row_render_height(self, row, text_renderer):

        # Which items apply?
        (a, b) = (
            (row * self.per_row),
            (row * self.per_row) + self.per_row
        )

        # Clamp bounds if necessary.
        # Note that we clamp based on desired parameters for a range() statement, so it's inclusive.
        if ( b > len(self.widgets) ):

            # Clamp
            b = len(self.widgets) 


        # Get max of said items...
        try:
            return max( self.widgets[i].get_render_height(text_renderer) for i in range(a, b) )

        # 0 item list?
        except:

            logn( "rowmenu group error", sys.exc_info() )
            logn( "rowmenu group error", "Aborting:  0 items in group!" )
            sys.exit()

            return 0


    # Find the tallest widget render height within this group
    def get_max_render_height_in_group(self, text_renderer):

        # Max
        return max( widget.get_render_height(text_renderer) for o in self.widgets )


    # Find the tallest widget box height within this group
    def get_max_box_height_in_group(self, text_renderer):

        # Max
        return max( widget.get_box_height(text_renderer) for o in self.widgets )


    def get_min_x(self, text_renderer):

        return min( o.get_min_x(text_renderer) for o in self.widgets )


    # Get an item from within this group only
    def get_item_by_id(self, param):

        # Loop wrapped items in each group
        for widget in self.widgets:

            # Check raw widget id
            if ( widget.get_id() == param ):

                # Return the wrapped item
                return widget

        # Not found...
        return None


    # Try to find a widget nested anywhere within the group, even if it's in a deeply nested widget
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


    def handle_user_input(self, control_center, universe):

        # Events that arise from user input
        results = EventQueue()

        for widget in self.widgets:

            results.append(
                widget.handle_user_input(control_center, universe)
            )

        # Return events
        return results


    def process(self, control_center, universe):#user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):
        self.invalidate_cached_metrics()

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        for widget in self.widgets:

            results.append(
                widget.process(control_center, universe)
            )


        # Return events
        return results



    def draw(self, rowmenu, r1, r2, active_widget, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        r2 = offset_rect(
            r2,
            x = self.hslide_controller.get_interval(),
            y = self.vslide_controller.get_interval()
        )

        #print "parent widget:  ", rowmenu.debug, rowmenu

        qq = []

        (u, v) = (r2[0], r2[1])

        index = 0

        # Initial rendering position
        (x, y) = (
            r2[0],
            r2[1]# + self.get_padding_top()
        )


        # Render point
        (rx, ry) = (
            r2[0] + self.get_x(),
            r2[1]
        )

        # Dimensions
        (width, height) = (
            r2[2],
            self.report_widget_height(text_renderer)
        )


        # Fit to width?
        if (self.fit_width):

            # Default to full width
            width = width

            # If we don't have enough items to fill an entire row, we will lessen the width
            if ( len(self.widgets) < self.per_row ):

                # Determine the width we really need
                width = ( len(self.widgets) * self.get_cell_width() ) + ( (len(self.widgets) - 1) * self.column_padding )

                # Don't go negative, though (i.e. no items means a width of 0)
                if (width < 0):

                    width = 0


        # Center horizontally?
        if (self.halign == "center"):

            # Adjust by half width
            rx -= int(width / 2)


        # Remember that initial data for delta calculation...
        (ox, oy) = (
            x,
            y
        )


        # Use widget's very own alpha data
        alpha = self.alpha_controller.get_interval()


        stencil_controller = window_controller.get_stencil_controller()


        # Place a border around the item group?
        if (self.render_border):

            alpha_factor = self.get_background_alpha()#rowmenu.get_gradient_alpha_factor(disabled = disabled, highlight = highlighted)

            # Because this RowMenuGroup uses a frame, we're going to enable the stencil buffer before we draw it
            # in order to establish the screen region on which we can draw afterward.  (Useful for fitting
            # rectangle fills within rounded corners, for instance.)
            stencil_controller.clear()

            # Enable painting, as we prepare to define the renderable area
            stencil_controller.set_mode(STENCIL_MODE_PAINT)

            # Now, render the border.
            #window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(r1[0] - border_offset, r1[1] - border_offset, self.get_width() + (2 * border_offset), global_frame_height + (2 * border_offset), background1, background2, border = border, border_size = border_size, shadow = shadow, shadow_size = shadow_size, gradient_direction = gradient_direction, radius = 10)

            #"""
            window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                rx,
                ry,# + self.get_margin_top(),
                width,
                height,#self.get_render_height(text_renderer), # + self.get_padding_top() ,
                background1 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_start() ), #rowmenu.get_gradient_color1(disabled = disabled, highlight = highlighted)),
                background2 = set_alpha_for_rgb( alpha_factor * alpha, self.get_gradient_end() ), #rowmenu.get_gradient_color2(disabled = disabled, highlight = highlighted)),
                border = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ), #rowmenu.get_border(disabled = disabled, highlight = highlighted)),
                border_size = 0,#rowmenu.get_border_size(), #rowmenu.get_border_size(disabled = disabled, highlight = highlighted),
                shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ), #rowmenu.get_shadow(disabled = disabled, highlight = highlighted)),
                shadow_size = 0,#rowmenu.get_shadow_size(), #rowmenu.get_shadow_size(disabled = disabled, highlight = highlighted),
                gradient_direction = self.get_gradient_direction(), #rowmenu.get_gradient_direction(disabled = disabled, highlight = highlighted),
                radius = 10
            )


            # Set the stencil controller to erase mode before rendering the border
            stencil_controller.set_mode(STENCIL_MODE_ERASE)

            # Render the frame itself, in the process marking its frame as un-writeable to anything else (leaving only the inside region as writeable)
            window_controller.get_geometry_controller().draw_rounded_rect_frame(
                rx,
                ry,# + self.get_padding_top(),
                width,
                height,#self.get_render_height(text_renderer), # + self.get_padding_top() ,
                color = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ), #rowmenu.get_border(disabled = disabled, highlight = highlighted)),
                border_size = self.get_border_size(), #rowmenu.get_border_size(disabled = disabled, highlight = highlighted),
                shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ), #rowmenu.get_shadow(disabled = disabled, highlight = highlighted)),
                shadow_size = self.get_shadow_size(), #rowmenu.get_shadow_size(disabled = disabled, highlight = highlighted),
                radius = 10
            )
            #"""

            # If this group wants to have a title bar (typically a rectangle under the first item),
            # then we'll BRIEFLY enable stencil testing on the region we just painted to...
            if (self.uses_title_bar):

                #window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (225, 225, 25, 0.25))
                #window_controller.get_geometry_controller().draw_rect(0, 0, 320, 480, (225, 25, 25, 0.25))
                stencil_controller.set_mode(STENCIL_MODE_PAINTED_ONLY)
                #window_controller.get_geometry_controller().draw_rect(160, 0, 320, 480, (225, 225, 25, 0.25))
                stencil_controller.lock()


            # Otherwise, forget about the stencil impressions we just painted.
            else:

                stencil_controller.set_mode(STENCIL_MODE_PAINTED_ONLY)


        for i in range(0, len(self.widgets)):

            # Convenience
            widget = self.widgets[i]


            # x position depends on the row index against columns per row...
            index_x = (i % self.per_row)

            #item_x = ( max(0, (index_x) * item_group.column_padding) ) + ( index_x * item_group.get_cell_width() )
            item_x = index_x * (self.get_cell_width() + self.column_padding)


            # Determine rendering position
            r3 = (rx + item_x, ry + self.get_padding_top(), self.get_cell_width(), self.get_row_render_height( self.get_row_by_widget_index(i), text_renderer ) )

            # On-the-fly indentation based on y-axis location.  Typically (default) returns 0...
            r3 = offset_rect(r3, x = rowmenu.f_calculate_indentation(r3[1] + int(r3[3] / 2)))


            # Determine initial visibiltty by ... visibility testing?
            visible = intersect_y(r1, r3)

            #"""
            # Before we get to business, let's see if we want to skip rendering of this item,
            # depending on its explicit visibility setting...
            if (widget.visibility == "with-parent"):

                # In this case, we only render this widget if its parent is the current selection...
                active_widget = rowmenu.get_active_widget()

                # Try to get the parent widget now
                parent_widget = rowmenu.get_widget_by_id( widget.parent_id )

                # If it's not the same widget, we will bail...
                if ( not (parent_widget == active_widget) ):

                    # Don't render this widget...
                    visible = False

            elif (0):#item.hidden):

                # Never render hidden items
                visible = False
            #"""

            #window_controller.get_geometry_controller().draw_rect(r2[0], r2[1], r2[2], r2[3], (225, 25, 25, 0.25))


            #print "%s offset by %s" % (r2, rowmenu.f_calculate_indentation(r2[1]))

            #window_controller.get_geometry_controller().draw_rect(r2[0], r2[1], r2[2], r2[3], (25, 225, 25, 0.25))

            #print r1, r2
            #print i, r1, r2

            # Cull non-visible rows
            if (visible):

                # Call on awake handler to process any lazy loading, etc.
                widget.while_awake()


                alpha_factor = widget.get_background_alpha()

                if ( (rowmenu.uses_focus) and ( rowmenu.is_focused() and rowmenu.uses_focus ) and (widget == active_widget) ):

                    if (0 and widget.render_border):

                        window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                            r3[0],
                            r3[1],
                            r3[2],
                            r3[3],
                            background1 = set_alpha_for_rgb(alpha_factor * alpha, widget.get_gradient_start() ),#color1(disabled = disabled, highlight = highlighted)),
                            background2 = set_alpha_for_rgb(alpha_factor * alpha, widget.get_gradient_end() ),#rowmenu.get_gradient_color2(disabled = disabled, highlight = highlighted)),
                            border = widget.get_border_color(), #(disabled = disabled, highlight = highlighted),
                            border_size = widget.get_border_size(), #(disabled = disabled, highlight = highlighted),
                            shadow = widget.get_shadow_color(), #(disabled = disabled, highlight = highlighted),
                            shadow_size = widget.get_shadow_size(), #(disabled = disabled, highlight = highlighted),
                            gradient_direction = widget.get_gradient_direction()#disabled = disabled, highlight = highlighted)
                        )


                    # Render the contents of each cell
                    widget.draw( r3[0], r3[1], tilesheet_sprite, additional_sprites, text_renderer, window_controller )

                else:

                    # Render the contents of each cell
                    widget.draw( r3[0], r3[1], tilesheet_sprite, additional_sprites, text_renderer, window_controller )


            # Culled row
            else:

                # Call on asleep handler to clean up anything if necessary
                widget.while_asleep()


            #text_renderer.render("Offset:  %d, Render.y:  %d" % (rowmenu.get_y_offset_at_index(text_renderer, index), r3[1] - sy), r3[0], r3[1], (225, 25, 25))

            index += 1

            # Always increment the y tracker at the end of a row
            if ( ( (i % self.per_row) == (self.per_row - 1) ) or
                 ( i == self.count() - 1 ) ):

                # Advance by row height (i.e. clear the tallest item in the current row)
                ry += self.get_row_height(
                    self.get_row_by_widget_index(i),
                    text_renderer
                )

                z = self.get_row_height(
                    self.get_row_by_widget_index(i),
                    text_renderer
                )
                #log2( "Advance by:  %s" % z )


            # If this group uses a title bar, then we only apply that "effect" to
            # the leading item.  After we've rendered it, we stop caring about the stencil test.
            if ( (i == 0) and (self.uses_title_bar) ):

                # Unlock the stencil controller
                stencil_controller.unlock()

                # We're done with stencil mode; we rendered the title bar.
                stencil_controller.set_mode(STENCIL_MODE_NONE)

            #window_controller.get_geometry_controller().draw_rect_frame(r3[0], r3[1], r3[2], r3[3], (225, 225, 25, 0.5), 2)


        # Safety - Make sure we always disable the stencil test, even if this group has no item...
        if ( ( len(self.widgets) == 0 ) and ( self.uses_title_bar ) ):

            # Unlock the stencil controller
            stencil_controller.unlock()

            # We're done with stencil mode; we rendered the title bar.
            stencil_controller.set_mode(STENCIL_MODE_NONE)


        #window_controller.get_geometry_controller().draw_rect(rx, ry, width, self.get_box_height(text_renderer), (225, 225, 25, 0.45))

        """
        window_controller.get_geometry_controller().draw_rect(u, v, 100, self.get_box_height(text_renderer), (225, 225, 225, 0.45))
        window_controller.get_geometry_controller().draw_rect_frame(u, v, 100, self.get_box_height(text_renderer), (25, 225, 25, 0.45), 2)

        window_controller.get_geometry_controller().draw_rect(u, v, 100, self.report_widget_height(text_renderer), (225, 25, 25, 0.25))
        window_controller.get_geometry_controller().draw_rect_frame(u, v, 100, self.report_widget_height(text_renderer), (25, 25, 225, 0.25), 2)

        z = v + self.get_box_height(text_renderer) - text_renderer.font_height
        text_renderer.render_with_wrap(".%s:  %s %s, %s %s" % (self.css_class, self.get_margin_top(), self.get_margin_bottom(), self.get_padding_top(), self.get_padding_bottom()), u, z, (225, 25, 25))
        """

        #text_renderer.render_with_wrap(".%s:  %s %s, %s %s" % (self.get_bloodline(), self.get_margin_top(), self.get_margin_bottom(), self.get_padding_top(), self.get_padding_bottom()), u, v, (225, 225, 25))

        # If we rendered a border, then we're currently in painted only mode.
        if (self.render_border):

            # Turn it off
            stencil_controller.set_mode(STENCIL_MODE_NONE)

            #print "NO MORE STENCIL"
