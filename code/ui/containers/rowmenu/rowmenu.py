import sys
import time

from group import Group

from code.ui.common import UIWidget

from code.extensions.common import UITemplateLoaderExt

from code.tools.eventqueue import EventQueue

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_PROMPT_WIDTH, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_HOME, INPUT_SELECTION_END, INPUT_SELECTION_PAGEUP, INPUT_SELECTION_PAGEDOWN, INPUT_SELECTION_ACTIVATE, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, DATE_WIDTH, DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIALOGUE_PANEL_WIDTH, DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE, LITERAL_POSITION_TRANSLATIONS, TOOLTIP_MIN_PADDING_X, TOOLTIP_MIN_PADDING_Y
from code.constants.common import STENCIL_MODE_NONE, STENCIL_MODE_PAINT, STENCIL_MODE_ERASE, STENCIL_MODE_PAINTED_ONLY, STENCIL_MODE_UNPAINTED_ONLY

from code.constants.sound import *

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import evaluate_spatial_expression, intersect, intersect_y, offset_rect, log, log2, xml_encode, xml_decode, set_alpha_for_rgb, coalesce




class RowMenu(UIWidget):

    def __init__(self):#, x = 0, y = 0, width = 0, height = 0, cellpadding = 5, cellspacing = 10, global_frame = False, shrinkwrap = False, disabled = False, hide_scrollbar = False, center_vertically = False, uses_focus = True, active_indentation = 5, autoscroll = False, debug = "default"):

        # Inherit window properties stuff
        UIWidget.__init__(self, selector = "rowmenu")

        self.debug = False


        # State hasn't changed, we're loading from scratch!
        self.state_changed = False


        # Frame the entire RowMenu?
        self.global_frame = False


        # We might "shrinkwrap" the global frame to use only the height necessary
        self.shrinkwrap = False

        self.fixed_height = False

        # Disabled appearance?
        self.disabled = False


        # Prevent scrollbar from ever appearing?
        self.hide_scrollbar = False

        # Control which side of the RowMenu to render the scrollbar (defaults to right, as you'd expect)
        self.scrollbar_position = DIR_RIGHT


        # Vertical centering, on-the-fly?
        self.center_vertically = False

        # Custom horizontal alignment
        self.halign = "left" # left, center, bottom

        # Custom vertical alignment
        self.valign = "top" # top, center, bottom


        # Is the menu active?
        self.active = False


        # Will this RowMenu response to input if it has focus?
        self.uses_focus = True

        # Does it care about scroll position?
        self.uses_scroll = True


        # Track the cursor position
        self.cursor = 0

        # How far (if at all) do we indent the highlighted item?
        self.active_indentation = 5 # hard-coded

        # Will anything happen on cursor change?
        self.onchange = None


        # Events
        self.on_wrap_left = None
        self.on_wrap_right = None

        self.on_wrap_up = None
        self.on_wrap_down = None

        self.on_change = ""


        # Scroll offset
        self.scroll = 0

        # Sometimes we want to autoscroll through a RowMenu (such as a text readout)
        self.autoscroll = False

        # to which item should we scroll?
        self.autoscroll_target = 0

        # Do we want to wait for a period of time before processing the autoscroll?
        self.autoscroll_delay = 0

        # Speed
        self.autoscroll_speed = 5


        # We can specify a special function to control indentation of each item according
        # to its offset relative to an arbitrary screen location.  By default, there is no indentation.
        self.f_calculate_indentation = lambda y: 0


        # Track the item groups (these often will be "groups" of one single item)
        self.groups = []

        # We can set a RowMenu to "tunnel" any input it receives to an item (given a particular item id).
        # Ordinarily, each item (row) in the RowMenu receives no direct input; the RowMenu keeps it to itself.
        # This functionality, though, bypasses the RowMenu object and sends the input to a given item...
        self.tunnel_target_id = ""


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        """
        if ( "max-width" in options ):
            if ( "%s" % options["max-width"] == "0" ):

                log( self.get_bloodline() )
                log( options )
                log( 5/0 )
        """

        if ( "center-vertically" in options ):
            self.center_vertically = ( int( options["center-vertically"] ) == 1 )

        if ( "halign" in options ):
            self.halign = options["halign"]

        if ( "valign" in options ):
            self.valign = options["valign"]

        if ( "global-frame" in options ):
            self.global_frame = ( int( options["global-frame"] ) == 1 )

        if ( "active-indentation" in options ):
            self.active_indentation = int( options["active-indentation"] )

        if ( "shrinkwrap" in options ):
            self.shrinkwrap = ( int( options["shrinkwrap"] ) == 1 )

        if ( "fixed-height" in options ):
            self.fixed_height = ( int( options["fixed-height"] ) == 1 )

        if ( "uses-focus" in options ):
            self.uses_focus = ( int( options["uses-focus"] ) == 1 )

        if ( "uses-scroll" in options ):
            self.uses_scroll = ( int( options["uses-scroll"] ) == 1 )

        if ( "autoscroll" in options ):
            self.autoscroll = ( int( options["autoscroll"] ) == 1 )

        if ( "scrollbar-position" in options ):
            self.scrollbar_position = int( LITERAL_POSITION_TRANSLATIONS[ options["scrollbar-position"] ] )

        if ( "tunnel-target-id" in options ):

            # Update target
            self.tunnel_target_id = options["tunnel-target-id"]


            # Try to find that widget...
            widget = self.get_widget_by_id(self.tunnel_target_id)

            # Found it?
            if (widget):

                # Blur self
                self.blur()

                # Focus on the raw widget
                widget.focus()

            # Couldn't find it, or we're resetting target id to empty string (no tunnel target)
            else:

                # I guess blur first, to cascade?
                self.blur()

                # Focus self
                self.focus()


        if ( "custom-indentation-callback" in options ):
            self.f_calculate_indentation = options["custom-indentation-callback"]


        if ( "on-wrap-up" in options ):
            self.on_wrap_up = options["on-wrap-up"]

        if ( "on-wrap-down" in options ):
            self.on_wrap_down = options["on-wrap-down"]

        if ( "on-wrap-left" in options ):
            self.on_wrap_left = options["on-wrap-left"]

        if ( "on-wrap-right" in options ):
            self.on_wrap_right = options["on-wrap-right"]

        if ( "on-change" in options ):
            self.on_change = options["on-change"]


        # For chaining
        return self


    # Configure the alpha controller, then cascade
    def configure_alpha_controller(self, options):

        # Standard alpha configuration
        UIWidget.configure_alpha_controller(self, options)

        # Cascade to groups
        for group in self.groups:

            # Cascade
            group.configure_alpha_controller(options)


    # Save RowMenu state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Add in a few state details specific to this RowMenu
        details_node = root.add_node(
            XMLNode("rowmenu")
        )

        # Save cursor location
        details_node.set_attributes({
            "cursor.y": self.cursor
        })


        # Create a node to track each item group in the RowMenu
        groups_node = root.add_node(
            XMLNode("groups")
        )

        # Save state of each Group
        for i in range( 0, len(self.groups) ):

            # Add Group state
            groups_node.add_node(
                self.groups[i].save_state()
            )


        # Return node
        return root


    # Load RowMenu state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Grab details specific to this RowMenu
        details_node = node.find_node_by_tag("rowmenu")

        # Validate
        if (details_node):

            # Restore cursor
            self.cursor = int( details_node.get_attribute("cursor.y") )

        # Check for item group states
        groups_node = node.find_node_by_tag("groups")

        # Validate
        if (groups_node):

            # Set state for each widget
            group_node_collection = groups_node.get_nodes_by_tag("*")

            # Loop all groups
            for i in range( 0, len(self.groups) ):

                # Sanity
                if ( i < len(group_node_collection) ):

                    # Restore Group state
                    self.groups[i].load_state( group_node_collection[i] )


    # Invalidate cached metrics
    #def invalidate_cached_metrics(self):


    # Get child widgets
    def get_child_widgets(self):

        # Return all Groups
        return self.groups


    def save_state_as_xml(self):

        xml = """
            <cursor y = '%d' />
        """ % self.cursor

        return xml

    def load_state_from_xml(self, xml):

        # Generic node
        node = XMLParser().create_node_from_xml(xml)


        # Load the cursor data
        ref_cursor = node.get_first_node_by_tag("cursor")

        if (ref_cursor):

            self.cursor = int( ref_cursor.get_attribute("y") )

    """ Event callbacks """
    # On birth, we should place the cursor at 0
    def handle_birth(self):

        # Track events
        results = EventQueue()

        """
        for group in self.groups:

            group.blur()

            results.append(
                group.handle_birth()
            )
        """


        """
        # Append results of moving cursor by "0"
        results.append(
            self.set_cursor(0) # Wake-up
        )
        """



        """
        # Check child widgets
        for widget in self.widgets:

            results.append(
                widget.handle_birth()
            )
        """


        # Return events
        return results


    # The RowMenu widget uses a custom on focus callback.
    # RowMenu widgets will give focus to the active Group (which contains active selection), and it will also take over Group's callback
    # duty, casting focus on the active selection within that Group.
    def on_focus(self):

        # Sanity
        if ( self.count() > 0 ):

            # Get the group index/offset at the current cursor location
            (group_index, group_offset) = self.get_group_index_and_offset_at_index(self.cursor)

            z = 0

            # Loop groups
            for i in range( 0, len(self.groups) ):

                if ( i == group_index ):

                    # Set focus on the Group
                    self.groups[i].css({
                        "bloodline": self.get_bloodline()
                    }).focus()

                    # Find the active item
                    for j in range( 0, len(self.groups[i].widgets) ):#self.groups[i].items:

                        if ( (z + j) == self.cursor ):

                            # Set focus on the item
                            self.groups[i].widgets[j].css({
                                "bloodline": self.groups[i].get_bloodline()
                            }).focus()

                            """
                            if (0):
                                for item_id in prev_item.friend_ids:

                                    friend_item = self.get_widget_by_id(item_id)

                                    if (friend_item):

                                        friend_item.get_widget().focus()
                            """

                        else:

                            # Blur the item
                            self.groups[i].widgets[j].css({
                                "bloodline": self.groups[i].get_bloodline()
                            }).blur()

                else:

                    # Blur the group
                    self.groups[i].css({
                        "bloodline": self.get_bloodline()
                    }).blur()

                    # Might as well stay consistent, do all of the focusing and blurring for the Group
                    for widget in self.groups[i].widgets:

                        # Blur each widget in this Group
                        widget.css({
                            "bloodline": self.groups[i].get_bloodline()
                        }).blur()


                z += self.groups[i].count()


    # The RowMenu will also use a custom on blur callback.
    # Like the on focus callback, this one blurs both the Groups and each Group's Widgets.  The Group itself doesn't control focus/blur.
    def on_blur(self):

        # Loop groups
        for group in self.groups:

            # Blur the group
            group.css({
                "bloodline": self.get_bloodline()
            }).blur()

            # Loop the Group's child widgets
            for widget in group.widgets:

                # Blur each widget
                widget.css({
                    "bloodline": group.get_bloodline()
                }).blur()


    # On resize, we must resize all rowmenu groups
    def on_resize(self, text_renderer = None):

        # Cascade
        for group in self.groups:

            group.configure({
                "width": "100%",
                "max-width": self.get_width()
            })

            if (text_renderer):

                group.configure({
                    "max-height": self.report_widget_height(text_renderer)
                })

            group.on_resize(text_renderer)


    def on_select(self):

        return None


    def count(self):

        return sum( o.count() for o in self.groups )


    def reset(self):

        self.groups = []


    # Add a new item group
    def add_group(self):

        self.groups.append(
            Group().configure({
                "width": self.get_width()
            })
        )

        # Set parent on new group to self
        self.groups[-1].set_parent(self)

        # For chaining
        return self.groups[-1]


    # Get all item groups
    def get_groups(self):

        return self.groups


    # Populate the RowMenu with groups, and populate those groups with items
    def populate_from_collection(self, cell_collection, control_center, universe, parent_group = None):#widget_dispatcher, cell_collection, universe, session, text_renderer = None, parent_group = None):

        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        for ref_cell in cell_collection:

            #print ref_cell.compile_xml_string()

            # Defined groups?
            if (ref_cell.tag_type == "item-group"):

                # First create a new group with the supplied properties
                group = self.add_group().configure(
                    ref_cell.set_attributes({
                        "bloodline": self.get_bloodline() # Inject bloodline into the attributes
                    }).get_attributes()
                )

                # Update css on the new item group
                group.__std_update_css__(control_center, universe)

                # Now load in all RowMenuItems for this group...
                cell_collection2 = ref_cell.get_nodes_by_tag("item")

                # The new item group is the parent...
                self.populate_from_collection(cell_collection2, control_center, universe, parent_group = group)#widget_dispatcher, cell_collection2, universe, session, parent_group = group)

            # Inline <item />; we'll create a Group for it on-the-fly...
            else:

                # "Inline" items (without a group) will receive their own group )a one-item group) on-the-fly
                group = parent_group

                if (group == None):

                    group = self.add_group().configure(     # This item didn't have a predefined group, so let's create one just for it
                        ref_cell.set_attributes({
                            "bloodline": self.get_bloodline() # Inject bloodline into the attributes
                        }).get_attributes()
                    )

                ref_cell.set_attributes({
                    "bloodline": group.get_bloodline(),
                    "max-width": group.get_cell_width()
                })


                # Now let's create a container for this item and populate it, ultimately adding it to the item group...
                """
                container = widget_dispatcher.convert_node_to_widget(ref_cell, control_center, universe).configure(
                    ref_cell.set_attributes({
                        "bloodline": group.get_bloodline(),
                        "max-width": group.get_cell_width()
                    }).get_attributes()
                )
                """
                container = widget_dispatcher.convert_node_to_widget(ref_cell, control_center, universe).configure(
                    ref_cell.get_attributes()
                )


                """
                # Declare this variable here to keep scope
                elem_collection = None

                # Does this item separate content into its own container?
                ref_contents = ref_cell.get_first_node_by_tag("contents")
                ref_tooltip = ref_cell.get_first_node_by_tag("tooltip")


                # Contents node holds the widgets
                if (ref_contents):

                    elem_collection = ref_contents.get_nodes_by_tag("*")

                # The cell itself is just a glob of widgets, no tooltip to speak of
                else:

                    # Populate the container (labels, etc.)
                    elem_collection = ref_cell.get_nodes_by_tag("*")
                """



                new_widget = group.add(container).configure(
                    ref_cell.set_attributes({
                        "xbloodline": group.get_bloodline() # Inject item group's bloodline into the node
                    }).get_attributes()
                )

                # Validate
                if (new_widget):

                    # Update css on the new item
                    new_widget.__std_update_css__(control_center, universe)


        # After population (and all sub-population), place the cursor at the beginning, if this is an active RowMenu...
        if ( (self.uses_focus) and ( self.count() > 0 ) and (not self.disabled) and (parent_group == None) ):

            self.set_cursor_at_beginning()

            # Force triggering of set_cursor with event callbacks
            self.set_cursor(self.cursor, prev_cursor = None)


        self.on_resize( control_center.get_window_controller().get_default_text_controller().get_text_renderer() )


        # For chaining
        return self


    # Loop through all Groups, returning each Group's child widgets
    # in one long flat list.
    def get_widgets_as_flat_list(self, debug = False):

        if (debug):
            log( "item groups:  ", self.groups )

        # Track list
        results = []

        # Loop Groups
        for group in self.groups:

            # Extend items
            results.extend(
                group.get_child_widgets()
            )

            if (debug):
                log( group )
                log( results )
                log( "" )

        # Return flat list of Widgets
        return results


    # Get a raw widget by id, within the item wrapper
    def get_widget_by_id(self, widget_id):

        # Group loop
        for group in self.groups:

            # Widget loop
            for widget in group.widgets:

                # Check the raw widget id, again...
                if ( widget.get_id() == widget_id ):

                    # Here, we return the raw widget
                    return widget

        # Couldn't find it
        return None


    # Get a raw widget by its rel attribute
    def get_widget_by_rel(self, rel):

        # Group loop
        for group in self.groups:

            # Widget loop
            for widget in group.widgets:

                # Check the raw widget id, again...
                if ( widget.get_rel() == rel ):

                    # Here, we return the raw widget
                    return widget

        # Couldn't find it
        return None


    # Try to find a group by its id
    def find_group_by_id(self, group_id):

        # Group loop
        for group in self.groups:

            # Single level check
            if ( group.get_id() == group_id ):

                # Found it
                return group

        # No group found
        return None


    # Try to find a widget nested anywhere within the rowmenu, even if it's in a deeply nested widget
    def find_widget_by_id(self, widget_id):

        # Group loop
        for group in self.groups:

            # Check each widget
            for widget in group.widgets:

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

    # Translate widgets within this RowMenu using a given hash
    def translate_environment_variables(self, h):

        # Group loop
        for group in self.groups:

            # Loop each widget in group
            for widget in group.widgets:

                # Do not descend into new namespaces
                if ( widget.get_namespace() == None ):

                    # Forward translations
                    widget.translate_environment_variables(h)


    # Get the widget at a given index offset
    def get_widget_at_index(self, index, debug = False):

        if (index < 0):

            return None

        else:

            widgets = self.get_widgets_as_flat_list(debug = debug)

            if (index < len(widgets)):

                return widgets[index]

            else:

                return None


    def get_y_offset_at_index(self, text_renderer, target_index, debug = False):

        # This one's easy...
        if (target_index == 0):

            return 0

        # Looping time...
        else:

            y = 0

            index = 0

            for j in range(0, len(self.groups)):

                # Convenience
                group = self.groups[j]

                # Does the item belong to this group?
                if (target_index in range(index, index + group.count())):

                    # Which row is the item on?
                    row = group.get_row_by_widget_index( (target_index - index) )

                    # Sum the heights of the previous rows to get the y position...
                    y += sum( group.get_row_height(r, text_renderer) for r in range(0, row) )

                    # We've calculated the offset
                    return y

                # No; we should just skip this group...
                else:

                    # Skip along the entire height
                    y += group.get_box_height(text_renderer)

                    # Increment the current index appropriately...
                    index += group.count()


            # Guess we couldn't find that item index...
            return 0


    def get_group_index_and_offset_at_index(self, target_index):

        # Easy!
        if (target_index == 0):

            return (0, 0)

        # Otherwise...
        else:

            index = 0

            for j in range(0, len(self.groups)):

                # Convenience
                group = self.groups[j]

                # Is it in this group?
                if (target_index in range(index, index + group.count())):

                    return (j, index)

                # Nope... keep looking...
                else:

                    index += group.count()


        # We didn't find it?
        return (-1, -1)


    # Determine at which item in the RowMenu a group begins
    def get_group_first_item_index_by_group_index(self, group_index):

        # Simple sum
        return sum( group.count() for group in self.groups[0 : group_index] )


    def get_cursor(self):

        return self.cursor


    def set_cursor(self, cursor, prev_cursor = None):

        # Events that arise from cursor placement
        results = EventQueue()


        # Set cursor
        self.cursor = cursor


        """ Begin HACK """
        # I maybe used to use tuples to define multi-column RowMenus.
        # Dumb.  Let's make sure we're in integer format, I guess?
        if ( type(self.cursor) == type( (1,) ) ):
            self.cursor = 0
        """ End HACK """


        # Did we really truly move the cursor anywhere?
        if (self.cursor != prev_cursor):

            self.focus()

            # Check for an on-change event
            if (self.on_change != ""):

                results.add(
                    action = self.on_change,
                    params = {
                        "widget": self
                    }
                )

            if (0):
                # Get the index of the group that contained the previously-cursored item
                (prev_group_index, prev_offset) = self.get_group_index_and_offset_at_index(prev_cursor)

                # Get the index of the group that contains the presently-cursored item
                (group_index, offset) = self.get_group_index_and_offset_at_index(self.cursor)


                # If the group index has changed, we must blur the old and focus on the new
                if (prev_group_index != group_index):

                    #log( "~~NEW GROUP~~" )

                    # Blur the previous group
                    self.groups[prev_group_index].blur()

                    # Focus on the new group
                    self.groups[group_index].focus()


                    # Focusing on the new group sends focus to all of its item (wrappers).  We don't want that.
                    # Let's blur every item in that group, before re-focusing on only the active item...
                    for widget in self.groups[group_index].widgets:

                        # Blur each child widget
                        widget.blur()


                    # Restore focus to the one item that should have focus
                    self.get_active_widget().focus()


                # Otherwise, we merely need to blur the previous item and focus on the new item...
                #else:

                # Blur the old one
                if (prev_cursor != None):

                    #self.get_widget_at_index(prev_cursor).get_widget().blur()

                    prev_widget = self.get_widget_at_index(prev_cursor)

                    """
                    prev_item.get_widget().blur()

                    for item_id in prev_item.friend_ids:

                        friend_item = self.get_widget_by_id(item_id)

                        if (friend_item):

                            friend_item.get_widget().blur()
                    """


                widget = self.get_widget_at_index(self.cursor)

                widget.focus()

                # Focus on the active one
                #self.get_active_widget().focus()

            """
            # Tell the old one we're through, history!
            if (prev_cursor != None):

                self.get_widget_at_index(prev_cursor).get_widget().blur()


            # Fetch the item at the new cursor location
            item = self.get_widget_at_index(self.cursor)


            # Tell the new widget we're ready to go...
            item.get_widget().focus()
            """


        # Return events
        return results

    def set_cursor_at_beginning(self, finalize = False):

        # Remember where we were...
        prev_cursor = self.cursor

        # Start at the top
        self.cursor = 0

        # Take the first non-disabled item
        while ( (self.cursor < self.count()) and (self.get_widget_at_index(self.cursor).disabled) ):

            self.cursor += 1

        # Don't overshoot
        if (self.cursor >= self.count()):

            self.cursor = self.count() - 1


        # Is this a hard call?
        if (finalize):

            # Finalize with an official set_cursor call (for firing callbacks and stuff)
            self.set_cursor(self.cursor, prev_cursor = prev_cursor)

    def set_cursor_at_end(self, finalize = False):

        # Remember where we were...
        prev_cursor = self.cursor

        # Start at the end
        self.cursor = self.count() - 1

        # Take the final non-dissabled row...
        while (self.get_widget_at_index(self.cursor).disabled):

            self.cursor -= 1


        # Is this a hard call?
        if (finalize):

            # Finalize with an official set_cursor call (for firing callbacks and stuff)
            self.set_cursor(self.cursor, prev_cursor = prev_cursor)


    # Set the cursor on a given widget object within any of the Groups
    def set_cursor_at_widget(self, widget):

        # Remember where we were...
        prev_cursor = self.cursor

        # Get widgets as a flat list
        widgets = self.get_widgets_as_flat_list()

        # Loop widgets
        for i in range( 0, len(widgets) ):

            # Object match?
            if ( widgets[i] == widget ):

                # Set cursor at index
                self.set_cursor(i, prev_cursor = prev_cursor)

    def step_by_item(self, direction):

        # Events that result from stepping (e.g. wrapping)
        results = EventQueue()


        if (direction == DIR_UP):

            # Note old cursor location
            cursor_index = self.cursor

            # We'll need to calculate this before we finish
            new_cursor = None

            while (new_cursor == None):

                # Go to the previos item
                cursor_index -= 1

                # Wrap back to the bottom of the RowMenu?
                if ( cursor_index < 0 ):

                    # From the beginning
                    cursor_index = ( self.count() - 1 )

                    # Track wrap event
                    if (self.on_wrap_up):

                        results.add(
                            action = self.on_wrap_up,
                            params = {
                                "widget": self
                            }
                        )


                # If the item at this index is disabled, we must continue...
                if ( self.get_widget_at_index(cursor_index).disabled ):

                    # We'll have to loop again...
                    pass

                # Otherwise, we've found a valid cursor position
                else:

                    new_cursor = cursor_index


            # Update the cursor position
            self.cursor = new_cursor#self.set_cursor(new_cursor, prev_cursor = prev_cursor)

            """
            if (self.cursor < 0):

                self.cursor = self.count() - 1

                # Wrap up event?
                if (self.on_wrap_up):

                    results.add(
                        action = self.on_wrap_up
                    )
            """

        elif (direction == DIR_DOWN):

            # Note old cursor location
            cursor_index = self.cursor

            # We'll need to calculate this before we finish
            new_cursor = None

            while (new_cursor == None):

                # Go to the next item
                cursor_index += 1

                # Wrap back to the top of the RowMenu?
                if ( cursor_index >= self.count() ):

                    # From the beginning
                    cursor_index = 0

                    # Track wrap event
                    if (self.on_wrap_down):

                        results.add(
                            action = self.on_wrap_down,
                            params = {
                                "widget": self
                            }
                        )


                # If the item at this index is disabled, we must continue...
                if ( self.get_widget_at_index(cursor_index).disabled ):

                    # We'll have to loop again...
                    pass

                # Otherwise, we've found a valid cursor position
                else:

                    new_cursor = cursor_index


            # Update the cursor position
            self.cursor = new_cursor#self.set_cursor(new_cursor, prev_cursor = prev_cursor)


        # Return events
        return results


    def step_by_group(self, direction):

        # Events that result from stepping (wrap, etc.)
        results = EventQueue()


        # Fetch metadata on whatever ItemGroup we're within at the moment
        (group_index, group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

        # Within that group, which row are we on?  (Param is relative within group)
        current_row = self.groups[group_index].get_row_by_widget_index( (self.cursor - group_index_offset) )

        # How many rows does the group have?
        total_rows = self.groups[group_index].count_rows()


        if (direction == DIR_UP):

            # If we're on the first row, we will need to go to the previous group
            if ( current_row == 0 ):

                # Prpeare to track the new cursor position
                new_cursor = None

                # Loop until we find a valid cursor location
                while (new_cursor == None):

                    # # Move to the previous group
                    group_index -= 1

                    # Wrap?
                    if ( group_index < 0 ):

                        # to the end
                        group_index = ( len(self.groups) - 1 )

                        # Track wrap event
                        if (self.on_wrap_up):

                            results.add(
                                action = self.on_wrap_up,
                                params = {
                                    "widget": self
                                }
                            )


                    # If the group we're looking at has no active item (or no item at all), we will have to loop some more...
                    if ( sum( int( not widget.disabled ) for widget in self.groups[group_index].widgets ) == 0 ):

                        # Try again at the next group...
                        pass

                    # Otherwise, specify the last item in this group as the new cursor location
                    else:

                        # Track
                        new_cursor = self.get_group_first_item_index_by_group_index(group_index) + self.groups[group_index].count() - 1

                        # We want to make sure to use the first active item, though...
                        while ( self.get_widget_at_index(new_cursor).disabled ):

                            # We know there is at least one active item in this group, somewhere...
                            new_cursor -= 1


                # Now we have found a valid cursor index
                self.cursor = new_cursor
                """
                # Previous!
                previous_group_index = group_index - 1

                # Will we need to wrap to the bottom?
                if (previous_group_index < 0):

                    previous_group_index = len(self.groups) - 1

                    # Track wrap event
                    if (self.on_wrap_up):

                        results.add(
                            action = self.on_wrap_up
                        )
                """

        elif (direction == DIR_DOWN):

            # If we're already on the last row, then we must advance to the next ItemGroup...
            if ( current_row == (total_rows - 1) ):

                # Remember previous cursor index
                prev_cursor = self.cursor

                # Prepare to track the new cursor position
                new_cursor = None

                # Loop until we decide...
                while (new_cursor == None):

                    # Advance to the next group
                    group_index += 1

                    # Wrap?
                    if ( group_index >= len(self.groups) ):

                        # Reset
                        group_index = 0

                        # Track wrap event
                        if (self.on_wrap_down):

                            results.add(
                                action = self.on_wrap_down,
                                params = {
                                    "widget": self
                                }
                            )


                    # If the group we're looking at has no active item (or no item at all), we will have to loop some more...
                    if ( sum( int( not widget.disabled ) for widget in self.groups[group_index].widgets ) == 0 ):

                        # Try again at the next group...
                        pass

                    # Otherwise, specify the first item in this group as the new cursor location
                    else:

                        # Track
                        new_cursor = self.get_group_first_item_index_by_group_index(group_index)

                        # We want to make sure to use the first active item, though...
                        while ( self.get_widget_at_index(new_cursor).disabled ):

                            # We know there is at least one active item in this group, somewhere...
                            new_cursor += 1


                # Now we have found the new cursor position
                self.cursor = new_cursor#self.set_cursor(new_cursor, prev_cursor = prev_cursor)


        # Return events
        return results


    def step_from_group(self, group_index, direction):

        if (direction == DIR_UP):

            group_index -= 1

            if (group_index < 0):

                group_index = len(self.groups) - 1

        elif (direction == DIR_DOWN):

            group_index += 1

            if (group_index >= len(self.groups)):

                # Do we have a wrap down handler?
                if (self.on_wrap_down):

                    # Only wrap if the wrap handler returns True...
                    if ( self.on_wrap_down(self) ):

                        return 0

                    # Otherwise, skip the wrap because the handler doesn't want us to wrap...
                    else:
                        return None


                # Nope; just wrap normally...
                else:
                    return 0

            else:
                return group_index

    def move_cursor(self, x, y, wrap = True):

        # Events that result from cursor movement (wrapping, etc.)
        results = EventQueue()


        # Remember where we were...
        prev_cursor = self.cursor


        # move on x-axis?
        if (x > 0):

            # Fetch metadata on current ItemGroup
            (group_index, group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

            # Need to know which row we're on.  (Param is relative within group)
            current_row = self.groups[group_index].get_row_by_widget_index( (self.cursor - group_index_offset) )

            # How many columns does that current row have?
            total_columns = self.groups[group_index].count_columns_in_row(current_row)

            # Which column are we on?
            current_column = self.groups[group_index].get_column_by_widget_index( (self.cursor - group_index_offset) )


            # If we have room to move over, then let's go ahead...
            if (current_column < (total_columns - 1)):

                self.cursor += 1

                # Never land on a disabled item
                while (self.get_widget_at_index(self.cursor).disabled):

                    self.cursor += 1

                    if (self.cursor >= self.count()):
                        self.cursor = 0

            # Otherwise, consider handling a wrap...
            else:

                if (self.on_wrap_right):

                    results.add(
                        action = self.on_wrap_right,
                        params = {
                            "widget": self
                        }
                    )


        elif (x < 0):

            # Fetch metadata on current ItemGroup
            (group_index, group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

            # Need to know which row we're on.  (Param is relative within group)
            current_row = self.groups[group_index].get_row_by_widget_index( (self.cursor - group_index_offset) )

            # Which column are we on?
            current_column = self.groups[group_index].get_column_by_widget_index( (self.cursor - group_index_offset) )


            # If we have room to move over, then let's go ahead...
            if (current_column > 0):

                self.cursor -= 1

                # Never land on a disabled item
                while (self.get_widget_at_index(self.cursor).disabled):

                    self.cursor -= 1

                    if (self.cursor < 0):
                        self.cursor = self.count() - 1

            # Otherwise, consider handling a wrap...
            else:

                if (self.on_wrap_left):

                    results.add(
                        action = self.on_wrap_left,
                        params = {
                            "widget": self
                        }
                    )

        # Move on y-axis?
        elif (y > 0):

            # Fetch metadata on whatever ItemGroup we're within at the moment
            (group_index, group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

            #print self.cursor, group_index, group_index_offset
            #print self.groups
            if (self.groups == []):
                #print "???"
                return results

            # Within that group, which row are we on?  (Param is relative within group)
            current_row = self.groups[group_index].get_row_by_widget_index( (self.cursor - group_index_offset) )

            # Which column are we currently on within that row?
            current_column = self.groups[group_index].get_column_by_widget_index( (self.cursor - group_index_offset) )

            # How many rows does the group have?
            total_rows = self.groups[group_index].count_rows()


            # If we're already on the last row, then we must advance to the next ItemGroup...
            if (current_row == (total_rows - 1)):

                # Go to the next group (that has at least one active item), first item in the group
                results.append(
                    self.step_by_group(DIR_DOWN)
                )

                """
                # Next!
                next_group_index = self.step_from_group(group_index, DIR_DOWN)# + 1

                if (next_group_index != None):

                    # Will we need to wrap to the top?
                    if (next_group_index >= len(self.groups)):

                        next_group_index = 0

                        # Track wrap event
                        if (self.on_wrap_down):

                            results.add(
                                action = self.on_wrap_down
                            )

                    # For now, let's just default the cursor to the first item in that new group...
                    self.cursor = sum( o.count() for o in self.groups[0 : next_group_index] )

                    # Don't land on a disabled item...
                    while (self.get_widget_at_index(self.cursor).disabled):

                        self.step_by_item(DIR_DOWN)
                """


                # Wherever we've ultimately landed, we're in the first row.  At this point, I want to try to remain in the same column
                # we originally occupied, if it's possible.
                (new_group_index, new_group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

                # Which row did we land on?
                new_row = self.groups[new_group_index].get_row_by_widget_index( (self.cursor - new_group_index_offset) )

                # The new column index (we're at the left-most column)
                new_column = self.groups[new_group_index].get_column_by_widget_index( (self.cursor - new_group_index_offset) )

                # We're presently at the left-most column.  If we were at a greater column index, then
                # we'll try to move over by the difference...
                if (current_column > new_column):

                    # What's the column difference?
                    delta = (current_column - new_column)

                    # Does this row have enough columns to support that delta?
                    new_row_column_count = self.groups[new_group_index].count_columns_in_row(new_row)

                    # If so, then we'll adjust accordingly...
                    if (new_row_column_count > (new_column + delta)):

                        self.cursor += delta

                        # Again, though, don't land on a disabled item...
                        if (self.get_widget_at_index(self.cursor).disabled):

                            # Just forget about the column matching thing
                            self.cursor -= delta

                    # Otherwise, I'm going to go over as far as I can...
                    else:

                        # Clamp delta
                        delta = (new_row_column_count - 1)


                        # Move over as far as we can...
                        self.cursor += delta

                        # Again, though, don't land on a disabled item...
                        if (self.get_widget_at_index(self.cursor).disabled):

                            # Just forget about the column matching thing
                            self.cursor -= delta

            # Otherwise, we're free to move down by per-row... probably...
            else:

                # Go down by per-row first
                self.cursor += self.groups[group_index].per_row

                # If we've exceeded the length of the group, though, we'll back up...
                limit = 0*1 + -1 + sum( o.count() for o in self.groups[0 : group_index + 1] )

                if (self.cursor > limit):
                    self.cursor = limit

                # Never land on a disabled item...
                while (self.get_widget_at_index(self.cursor).disabled):

                    results.append(
                        self.step_by_item(DIR_DOWN)
                    )

                    """
                    self.cursor += 1

                    # Wrap back to the top
                    if (self.cursor >= self.count()):

                        self.cursor = 0

                        # Track wrap event
                        
                            results.add(
                                action = self.on_wrap_right
                            )
                    """


            # Did we end up wrapping?  If so, let's see if we want to scoot the cursor back to the end
            if ( (not wrap) and (self.cursor < prev_cursor) ):

                self.set_cursor_at_end(finalize = False)

        elif (y < 0):

            # Fetch metadata on whatever ItemGroup we're within at the moment
            (group_index, group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

            # Within that group, which row are we on?  (Param is relative within group)
            current_row = self.groups[group_index].get_row_by_widget_index( (self.cursor - group_index_offset) )

            # Which column are we currently on within that row?
            current_column = self.groups[group_index].get_column_by_widget_index( (self.cursor - group_index_offset) )


            # If we're already on the first row, then we must retreat to the previous ItemGroup...
            if (current_row == 0):

                results.append(
                    self.step_by_group(DIR_UP)
                )

                """
                # Previous!
                previous_group_index = group_index - 1

                # Will we need to wrap to the bottom?
                if (previous_group_index < 0):

                    previous_group_index = len(self.groups) - 1

                    # Track wrap event
                    if (self.on_wrap_up):

                        results.add(
                            action = self.on_wrap_up
                        )
                """

                """
                # For now, let's just default the cursor to the last item in that new group...
                self.cursor = -1 + sum( o.count() for o in self.groups[0 : previous_group_index + 1] )

                # Don't land on a disabled item...
                while (self.get_widget_at_index(self.cursor).disabled):

                    #self.cursor -= 1
                    results.append(
                        self.step_by_item(DIR_UP)
                    )

                    #if (self.cursor < 0):
                    #    self.cursor = self.count() - 1
                """


                # Wherever we've ultimately landed, we're in a row.  At this point, I want to try to remain in the same column
                # we originally occupied, if it's possible.
                (new_group_index, new_group_index_offset) = self.get_group_index_and_offset_at_index(self.cursor)

                # Which row did we land on?
                new_row = self.groups[new_group_index].get_row_by_widget_index( (self.cursor - new_group_index_offset) )

                # The new column index (we're at the right-most column)
                new_column = self.groups[new_group_index].get_column_by_widget_index( (self.cursor - new_group_index_offset) )

                # We're presently at the right-most column.  If we were at a lesser column index, then
                # we'll try to move over by the difference...
                if (current_column < new_column):

                    self.cursor -= (new_column - current_column)

                    # Again, though, don't land on a disabled item...
                    if (self.get_widget_at_index(self.cursor).disabled):

                        # Just forget about the column matching thing
                        self.cursor += (new_column - current_column)


            # Otherwise, we're free to move up by per-row... always!  (A row above will always have >= the columns as any given row below it)
            else:

                # Go down by per-row first
                self.cursor -= self.groups[group_index].per_row

                # Never land on a disabled item...
                while (self.get_widget_at_index(self.cursor).disabled):

                    """
                    self.cursor -= 1

                    if (self.cursor < 0):
                        self.cursor = self.count() - 1
                    """
                    results.append(
                        self.step_by_item(DIR_UP)
                    )


            # Did we end up wrapping?  If so, let's see if we want to scoot the cursor back to the start
            if ( (not wrap) and (self.cursor > prev_cursor) ):

                self.set_cursor_at_beginning(finalize = False)


        # Return events
        return results


    # Determine how far the scroll bar will move when we place the cursor on a given item
    def get_scroll_offset_at_item_index(self, index, text_renderer):

        # Might we need a scrollbar to the side?
        total_height = self.calculate_contents_height(text_renderer)

        # Determine the maximum scroll amount
        max_scroll = ( total_height - self.get_height(text_renderer) )


        # First scroll all the way down to the item
        scroll = self.get_y_offset_at_index(text_renderer, index)

        # Attempt to center the current item vertically (up by half its box height)
        scroll -= ( int( self.get_height(text_renderer) / 2 ) - int( self.get_widget_at_index(index).get_box_height(text_renderer) / 2 ) )

        # Don't scroll into negative territory, though...
        if (scroll < 0):

            scroll = 0

        # Also avoid excess scrolling
        elif (scroll > max_scroll):

            scroll = max_scroll

        # Return calculation
        return scroll


    def autoscroll_to_index(self, index, delay = 0):

        # Make sure we're in bounds...
        if ( index < self.count() ):

            self.autoscroll_target = index

            # Track delay
            self.autoscroll_delay = delay

    def autoscroll_n_steps(self, n, delay = 0, wrap = True):

        # Increment with no regard for bounds
        self.autoscroll_target += n

        # Track delay
        self.autoscroll_delay = delay


        # Now check bounds / wrap...
        if ( self.autoscroll_target >= self.count() ):

            if (wrap):
                self.autoscroll_target = 0

            else:
                self.autoscroll_target = ( self.count() - 1 )

        elif ( self.autoscroll_target < 0 ):

            if (wrap):
                self.autoscroll_target = ( self.count() - 1 )

            else:
                self.autoscroll_target = 0


    def handle_user_input(self, control_center, universe):

        # Events resulting from user input
        results = EventQueue()


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # Remember previous cursor location; if it changes, we'll use the blur/focus callbacks on the old/new positions...
        prev_cursor = self.cursor


        # If this RowMenu doesn't use focus, we'll lock the input controller
        if (not self.uses_focus):

            input_controller.lock_all_input()


        # Did we configure this RowMenu to tunnel its input to one its items?  Let's try...
        target_widget = None

        # Make sure we explicitly specified a target
        if (self.tunnel_target_id != ""):

            # Try to find that widget...
            widget = self.get_widget_by_id(self.tunnel_target_id)

            # Found it?
            if (widget):

                # We want the raw widget
                target_widget = widget


        # Do we have a target to tunnel to?
        if (target_widget):

            results.append(
                target_widget.handle_user_input(control_center, universe)
            )

            #log( results._get_queue() )

            # Forward processing; return results
            #return xxx

        # Otherwise, handle input locally (as a normal RowMenu would)
        else:

            # Use gameplay input as user input from input controller
            user_input = input_controller.get_gameplay_input()

            # Why bother checking keyboard input if we don't ever use it?
            if (1):#self.uses_focus):

                if (INPUT_SELECTION_UP in user_input):

                    results.append(
                        self.move_cursor(0, -1)
                    )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)#, user_input, network_controller, universe, session, save_controller)

                elif (INPUT_SELECTION_DOWN in user_input):

                    results.append(
                        self.move_cursor(0, 1)
                    )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)#, user_input, network_controller, universe, session, save_controller)

                elif (INPUT_SELECTION_LEFT in user_input):

                    results.append(
                        self.move_cursor(-1, 0)
                    )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)

                elif (INPUT_SELECTION_RIGHT in user_input):

                    results.append(
                        self.move_cursor(1, 0)
                    )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)

                elif (INPUT_SELECTION_HOME in user_input):

                    self.set_cursor_at_beginning(finalize = True)

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)

                elif (INPUT_SELECTION_END in user_input):

                    self.set_cursor_at_end(finalize = True)

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)

                elif (INPUT_SELECTION_PAGEUP in user_input):

                    for i in range(0, 3):

                        results.append(
                            self.move_cursor(0, -1, wrap = False)
                        )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)

                elif (INPUT_SELECTION_PAGEDOWN in user_input):

                    for i in range(0, 3):

                        results.append(
                            self.move_cursor(0, 1, wrap = False)
                        )

                    # Tick sound effect
                    control_center.get_sound_controller().queue_sound(SFX_MENU_CURSOR)

                    if (self.onchange):
                        self.onchange(self)

                elif (INPUT_SELECTION_ACTIVATE in user_input):

                    # Try to get the RowMenu item at the current cursor
                    widget = self.get_widget_at_index(self.cursor)

                    # Validate
                    if (widget):

                        # Because this RowMenu handled the input event, I'm going to mark it as the "source" / "calling" widget
                        results.append(
                            widget.on_select().inject_params({
                                "widget": self
                            })
                        )

                        # Activate sound effect
                        control_center.get_sound_controller().queue_sound(SFX_MENU_SELECT)


            # Finalize with an official set_cursor call (for firing callbacks and stuff)
            results.append(
                self.set_cursor(self.cursor, prev_cursor = prev_cursor)
            )


        # If we locked it previously, unlock input now...
        if (not self.uses_focus):

            input_controller.unlock_all_input()


        # Return events
        return results


    def process(self, control_center, universe):#user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Process each item group
        for group in self.groups:

            results.append(
                group.process(control_center, universe)
            )


        # Return events
        return results


    def calculate_contents_height(self, text_renderer):

        return sum( group.get_box_height(text_renderer) for group in self.groups )

        return self.report_widget_height(text_renderer)
        return sum( (o.get_box_height(text_renderer) + 0) for o in self.groups ) - 0 # Don't need spacing after the final item group...


    # A RowMenu must sum the BOX height of each group it contains
    def report_widget_height(self, text_renderer):

        metric = self.get_cached_metric("reported-widget-height")
        #print metric, self

        if (metric != None):

            return metric

        else:

            if (self.fixed_height):

                metric = self.get_height(text_renderer)

            else:

                metric = sum( group.get_box_height(text_renderer) for group in self.groups )

            # Cache metric
            self.cache_metric("reported-widget-height", metric)

            # Return
            return metric


    def get_widget_height(self, text_renderer):

        return self.calculate_height(text_renderer)


    """
    # Get the active item wrapper
    def get_active_widget(self):

        return self.get_widget_at_index(self.cursor)
    """


    # Get the active widget (the raw widget within the active item wrapper)
    def get_active_widget(self):

        # Look for a tunnel widget (e.g. nested RowMenu)
        widget = self.get_widget_by_id(self.tunnel_target_id)

        # Found it?
        #if (widget):
        if (False):

            # Return nested result
            return widget.get_active_widget()

        # This RowMenu has focus
        else:

            # Get widget at current cursor position
            widget = self.get_widget_at_index(self.cursor)

            # Validate
            if (widget):

                return widget

            # Out of range
            else:

                return None


    # Get the group that contains the active widget
    def get_active_group(self):

        # First, calculate the index offset of this group
        (group_index, offset) = self.get_group_index_and_offset_at_index(self.cursor)

        # Return the item group
        return self.groups[group_index]


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller, offset_x = 0, offset_y = 0):

        """ Sanity / insanity """
        # No sense rendering an empty RowMenu
        if (self.count() == 0):

            return


        # Automatic custom-fit height calculation?
        # I"m not sure I use this anymore, and it sucks, but I'll leave it for now.
        if (self.get_height(text_renderer) == -1):

            self.configure({
                "height": self.report_widget_height(text_renderer)
            })



        """ Controllers """
        # Fetch the scissor controller;
        scissor_controller = window_controller.get_scissor_controller()

        # and the stencil controller
        stencil_controller = window_controller.get_stencil_controller()


        """ Rendering """
        # Render position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        #log2( self.vslide_controller.get_interval(), self.vslide_controller.get_target() )

        # Dimensions
        (width, height) = (
            self.get_width(),
            self.get_height(text_renderer)
        )


        # Use widget's very own alpha data
        alpha = self.alpha_controller.get_interval()


        # Does this RowMenu use a lightbox effect?
        if (self.uses_lightbox):

            # Render the lightbox as a percentage of the current alpha value
            window_controller.get_geometry_controller().draw_rect( 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, (DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE * alpha)) )
            #print (DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE * alpha)


        # Available rendering area...
        #r1 = (sx + self.get_x() - 0, sy + self.get_y() - 0, self.get_width() + 0, self.get_height(text_renderer) + 0)
        r1 = (rx, ry, width, height)

        # Do we prefer to center this thing vertically?
        if (self.center_vertically):

            # Needed to calculate alignment
            h = self.get_render_height(text_renderer)

            # Redefine the rendering area
            #r1 = (sx + self.get_x() - 0, int(SCREEN_HEIGHT / 2) - int(h / 2), self.get_width() + 0, h + 0)
            r1 = (rx, int(SCREEN_HEIGHT / 2) - int(h / 2), width, h)

            r1 = offset_rect(r1, y = self.vslide_controller.get_interval())

        elif (self.valign == "top"):

            pass

        elif (self.valign == "center"):

            h = self.get_height(text_renderer)

            if (self.shrinkwrap):

                # Determine overall RowMenu height
                h = self.get_render_height(text_renderer)

            # Center on the render location
            #r1 = offset_rect(r1, x = 0, y = -1 * int(h / 2))
            #r1 = ( sx + self.get_x(), int(SCREEN_HEIGHT / 2) - int(h / 2), self.get_width(), h )
            r1 = (rx, int(SCREEN_HEIGHT / 2) - int(h / 2), width, h)

            r1 = offset_rect(r1, y = self.vslide_controller.get_interval())

        elif (self.valign == "bottom"):

            h = self.get_height(text_renderer)

            if (self.shrinkwrap):

                # Determine overall RowMenu height
                h = self.get_render_height(text_renderer)

            # Use the render point as the lower edge of the RowMenu
            r1 = offset_rect(r1, x = 0, y = -h)


        if (self.halign == "left"):

            pass

        elif (self.halign == "center"):

            # Center on the screen
            r1 = ( int(SCREEN_WIDTH / 2) - int( width / 2 ), r1[1], width, r1[3] )

        elif (self.halign == "right"):

            # Use the render point as the right edge of the RowMenu
            r1 = offset_rect(r1, x = -width, y = 0)


        # Some sort of global offset, probably for the weird main menu sliding stuff
        r1 = offset_rect(r1, x = offset_x, y = offset_y)


        # Do we want to frame the entire viewable area?
        if (self.global_frame):

            # Decide on a background color scheme
            alpha_factor = self.get_background_alpha()#get_gradient_alpha_factor(disabled = self.disabled)


            # Decide how tall of a frame we'll render... full height by default...
            global_frame_height = self.get_height(text_renderer)

            # Best fit for the frame instead, perhaps?
            if (self.shrinkwrap):

                global_frame_height = min( self.get_height(text_renderer), self.get_render_height(text_renderer) )


            # Because this RowMenu uses a frame, we're going to enable the stencil buffer before we draw it
            # in order to establish the screen region on which we can draw afterward.  (Useful for fitting
            # rectangle fills within rounded corners, for instance.)
            stencil_controller.clear()

            # Enable painting, as we prepare to define the renderable area
            stencil_controller.set_mode(STENCIL_MODE_PAINT)


            window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                r1[0],
                r1[1],# + self.get_margin_top(),
                r1[2],
                self.get_render_height(text_renderer), # + self.get_padding_top() ,
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
                r1[0],
                r1[1],# + self.get_padding_top(),
                r1[2],
                self.get_render_height(text_renderer), # + self.get_padding_top() ,
                color = set_alpha_for_rgb( alpha_factor * alpha, self.get_border_color() ), #rowmenu.get_border(disabled = disabled, highlight = highlighted)),
                border_size = self.get_border_size(), #rowmenu.get_border_size(disabled = disabled, highlight = highlighted),
                shadow = set_alpha_for_rgb( alpha_factor * alpha, self.get_shadow_color() ), #rowmenu.get_shadow(disabled = disabled, highlight = highlighted)),
                shadow_size = self.get_shadow_size(), #rowmenu.get_shadow_size(disabled = disabled, highlight = highlighted),
                radius = 10
            )

            # From here until the end of this .draw() routine, we will only render to the area
            # on which we just drew the background...
            stencil_controller.set_mode(STENCIL_MODE_NONE)#PAINTED_ONLY)



        # Scissor on the rendering area
        scissor_controller.push( (0, r1[1], SCREEN_WIDTH, r1[3]) )


        #print "r1 = ", r1
        # Start at the top
        (x, y) = (
            r1[0] + 0,
            r1[1] + 0
        )

        # Remember original coordinates
        (ox, oy) = (x, y)



        """
        if (self.debug != "dynamic"):
            log( "cur_y = ", cur_y )
            log( "\tcursor:  ", self.cursor )
            log( "\tscroll:  ", self.scroll )
            log( "\tcalculated height:  ", self.calculate_height(text_renderer) )
            log( "\tsum heights:  ", sum( o.get_height(text_renderer, self.cellpadding) + (2 * self.cellpadding) for o in self.groups ) )
            #print "\tmin height:  ", min( o.get_height(text_renderer, self.cellpadding) + (2 * self.cellpadding) for o in self.groups )
            #print "\tmax height:  ", max( o.get_height(text_renderer, self.cellpadding) + (2 * self.cellpadding) for o in self.groups )

            (z1, z2) = self.get_group_index_and_offset_at_index(self.cursor)
            log( "\tsum heights[0 : %d]:  %s" % (z1, sum( o.get_height(text_renderer, self.cellpadding) + (2 * self.cellpadding) for o in self.groups[0 : z1] )) )
        """



        # Might we need a scrollbar to the side?
        total_height = self.calculate_contents_height(text_renderer)

        # Determine the maximum scroll amount
        max_scroll = ( total_height - self.get_height(text_renderer) )



        if (not self.autoscroll):

            if (self.uses_scroll and (max_scroll > 0)):

                self.scroll = self.get_scroll_offset_at_item_index(self.cursor, text_renderer)#self.get_y_offset_at_index(text_renderer, self.cursor)


        # RowMenus that don't use scroll will always render from the top
        if ( (not self.uses_scroll) and (not self.autoscroll) ):

            self.scroll = 0

        # Otherwise, let's check for the possible need of scrollbar...
        else:

            # Do we need to render a scrollbar?
            if ( ( total_height > self.get_height(text_renderer) ) and ( not self.hide_scrollbar ) ):

                # Padding between scrollbar and rowmenu (personal space!)
                padding = 10

                # Scrollbar dimensions
                scrollbar_width = 4
                scrollbar_height = int( (float( self.get_height(text_renderer) ) / float( total_height )) * self.get_height(text_renderer) )

                # Don't disappear, stay visible...
                if (scrollbar_height < 24):
                    scrollbar_height = 24

                # Calculate where to render the scrollbar cursor thing
                scrollbar_max_y = ( self.get_height(text_renderer) - scrollbar_height )
                scrollbar_y = int((float(self.scroll) / float(max_scroll)) * scrollbar_max_y)


                # Scope
                rScroll = None


                # Right-aligned scrollbar
                if (self.scrollbar_position == DIR_RIGHT):

                    # Define scrollbar region
                    rScroll = ( rx + width + padding, ry, scrollbar_width, self.get_height(text_renderer) )

                # Left-aligned scrollbar
                elif (self.scrollbar_position == DIR_LEFT):

                    # Define scrollbar region
                    rScroll = ( rx - padding, ry, scrollbar_width, self.get_height(text_renderer) )


                # If we're center-aligned, scrollbar needs adjusted
                if (self.halign == "center"):

                    rScroll = offset_rect(rScroll, x = -int(width / 2))

                # If we're right-aligned, we don't need += width
                elif (self.halign == "right"):

                    rScroll = offset_rect(rScroll, x = -width)

                # Ignore clipping
                window_controller.pause_clipping()

                # Render a background for the scrollbar
                window_controller.get_geometry_controller().draw_rect(rScroll[0], rScroll[1], rScroll[2], rScroll[3], (0, 0, 0, alpha))

                # Render scrollbar cursor / position indicator thing
                window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(rScroll[0], rScroll[1] + scrollbar_y, scrollbar_width, int(scrollbar_height / 2), (0, 0, 0, alpha), (225, 225, 225, alpha))
                window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(rScroll[0], rScroll[1] + scrollbar_y + int(scrollbar_height / 2), scrollbar_width, int(scrollbar_height / 2), (225, 225, 225, alpha), (0, 0, 0, alpha))

                # Resume clipping
                window_controller.resume_clipping()


        # Maybe we should process an autoscroll?
        if (self.autoscroll):

            # Do we need to delay?
            if (self.autoscroll_delay > 0):

                self.autoscroll_delay -= 1

            # Nope; let's move to where we want to be...
            else:

                # Calculate target offset
                target_scroll = self.get_y_offset_at_index(text_renderer, self.autoscroll_target)

                # Move in the necessary direction
                if (self.scroll < target_scroll):

                    self.scroll += self.autoscroll_speed

                    # Don't overshoot
                    if ( self.scroll > min(target_scroll, max_scroll) ):
                        self.scroll = min(target_scroll, max_scroll)

                # Fast-rewind
                elif (self.scroll > target_scroll):

                    self.scroll -= (3 * self.autoscroll_speed)

                    # Don't overshoot
                    if ( self.scroll < target_scroll ):
                        self.scroll = target_scroll


        # Render each visible item
        index = 0
        active_widget = self.get_widget_at_index(self.cursor)

        for j in range(0, len(self.groups)):

            # Convenience
            group = self.groups[j]


            r2 = ( x, y - self.scroll, group.get_group_width(), group.get_render_height(text_renderer) )


            packed_height = None

            # If we want to align it at the bottom...
            if (group.valign == "bottom"):

                # This only applies to non-scrolling lists, though...
                if ( total_height <= self.get_height(text_renderer) ):

                    widget_height = group.get_box_height(text_renderer)

                    r2 = (r2[0], sy + self.get_y() + (self.get_height(text_renderer) - widget_height), r2[2], widget_height)


            elif (group.valign == "center"):

                # Only the final item group can center itself (typically this means we have only one item group in the rowmenu)
                if ( j == ( len(self.groups) - 1 ) ):

                    height_used = sum( self.groups[v].get_box_height(text_renderer) for v in range(0, j) )

                    remaining_height = (self.get_height(text_renderer) - height_used)

                    # Make sure there's still room to center
                    if ( r2[3] < remaining_height ):

                        offset = int( (remaining_height - r2[3]) / 2 )

                        r2 = offset_rect(r2, y = offset)


            elif (group.valign == "pack"):

                if ( total_height <= self.get_height(text_renderer) ):

                    remaining_height = sum( self.groups[v].get_box_height(text_renderer) for v in range(j + 1, len(self.groups)) )

                    r2 = (r2[0], r2[1], r2[2], self.get_height(text_renderer) - (y - oy) - remaining_height)

                    packed_height = r2[3]


            #draw_rect_frame(r2[0], r2[1], r2[2], r2[3], (225, 25, 25, 0.75), 2)
            # Item group is visible?
            if (intersect(r1, r2)):

                # Make sure the stupid stencil controller is turned off
                stencil_controller.set_mode(STENCIL_MODE_NONE)

                # Call on awake handler in case it has any lazy loading
                group.while_awake()

                # Render item group (or at least part of it)
                group.draw( self, r1, r2, active_widget, tilesheet_sprite, additional_sprites, text_renderer, window_controller )

                #window_controller.get_geometry_controller().draw_rect(r2[0], r2[1], r2[2], r2[3], (25, 225, 25, 0.15))
                #window_controller.get_geometry_controller().draw_rect_frame(r2[0], r2[1], r2[2], r2[3], (225, 225, 25, 0.5), 1)

            else:

                #window_controller.get_geometry_controller().draw_rect(r2[0], r2[1], r2[2], r2[3], (225, 225, 25, 0.25))

                # Call on asleep handler in case it needs to drop anything when offscreen
                group.while_asleep()


            y += coalesce( packed_height, group.get_box_height(text_renderer) )

            #print "after group %d, y =  %d" % (j, y)

            index += group.count()


        # Disable stencil buffer, if/a
        if (window_controller):

            stencil_controller.set_mode(STENCIL_MODE_NONE)


        # Disable the last scissor test
        scissor_controller.pop()



        #window_controller.get_geometry_controller().draw_rect(u + 50, v, 100, self.report_widget_height(text_renderer), (25, 25, 125, 0.25))

        #if (self.css_class == "xxx"):
        #    window_controller.get_geometry_controller().draw_rect(r1[0], r1[1], r1[2], r1[3], (25, 25, 125, 0.25))


        #print "r1:  ", r1
        #if (self.debug != "dynamic"):
        #    draw_rect(r1[0], r1[1], r1[2], r1[3], (225, 25, 25, 0.25))

        """ DEBUG info """
        #window_controller.get_geometry_controller().draw_rect(r1[0], r1[1], r1[2], r1[3], (225, 25, 25, 0.25))
        #text_renderer.render("x, y, w, h, count:  %d, %d, %d, %d, %d" % (r1[0], r1[1], r1[2], r1[3], self.count()), r1[0], r1[1], (225, 225, 225, 0.6))
        """ End DEBUG info """

        #text_renderer.render("Focus:  %s" % self.is_focused(), r1[0], r1[1], (225, 25, 25, 0.6))

        #if (self.css_class == "debug2"):
        #    text_renderer.render("%s, %s" % (self.alpha_controller.get_interval(), self.alpha_controller.get_target()), r1[0], r1[1], (225, 225, 25, 0.6))



