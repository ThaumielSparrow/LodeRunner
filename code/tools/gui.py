import copy
import random

from extensions.guiextensions import GUIWidgetPopulationFunctions

from code.utils.common import *
from code.render.glfunctions import *

from code.tools.eventqueue import EventQueue, EventQueueIter

from code.ui.widget import Widget

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, CORNER_SIZE, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT


# Sigh.  Old code, from when I didn't know any better (?!)
def sub_str(string, a, b):
    return string[a:b]


# GUI Manager manages various GUI widgets, along with their events.
# It inherits from the common widget population functions.
class GUI_Manager(GUIWidgetPopulationFunctions):

    def __init__(self):

        GUIWidgetPopulationFunctions.__init__(self)


        # ?? (Obselete)
        self.sprites = {
        }


        # Default widget data (base style data, I guess)
        self.gui_defaults = {}


        # GUI widgets, hashed by name
        self.widgets = {}

        # Track widget order, by name
        self.widget_order = []


        # Track whether or not the gui manager's widget(s) performed mouse processing
        self.processed_mouse = False


        # GUI events
        self.pending_events = EventQueue()


    # Add a widget with a given name
    def add_widget_with_name(self, name, widget):

        # Force all widgets to have a name, hacky as it may be
        if (name == ""):

            # Auto-generate a useless name
            name = "untitled-widget%d" % (1 + len(self.widgets))


        # Save widget
        self.widgets[name] = widget

        # Track name in the widget order
        self.widget_order.append(name)


    # Get all widgets
    def get_widgets(self):

        # Here you go
        return self.widgets.values()


    # Get a widget, by name
    def get_widget_by_name(self, name):

        # Validate
        if (name in self.widgets):

            # Here you go
            return self.widgets[name]

        # 404
        else:
            return None


    # Get all direct-descendant widgets of a given type
    def get_widgets_by_selector(self, selector):

        # Matches
        results = []

        # Loop widgets
        for widget in self.widgets:

            # Match?
            if ( widget.selector == selector ):

                # Append
                results.append(widget)

        # Results
        return results


    # Render all widgets
    def draw_all(self, sx, sy, text_renderer, window_controller):

        # Loop in order added
        for name in self.widget_order:

            # Fetch widget
            widget = self.get_widget_by_name(name)

            # Validate
            if (widget):

                # Only render visible widgets
                if ( widget.is_visible() ):

                    # Render widget!
                    widget.draw(sx, sy, text_renderer, window_controller)

                    # Render overlays
                    widget.render_overlays(sx, sy, text_renderer, window_controller)


    # Render only those widgets at a given z index
    def draw_z_index(self, z, sx, sy, text_renderer, window_controller):

        # Loop in order added
        for name in self.widget_order:

            # Fetch widget
            widget = self.get_widget_by_name(name)

            # Validate
            if (widget):

                # Only render visible widgets
                if ( widget.alpha_controller.get_interval() > 0 ):

                    # Only render widgets that exist at the given z index
                    if (widget.z_index == z):

                        # Render widget!
                        widget.draw(sx, sy, text_renderer, window_controller)

                        # Render overlays
                        widget.render_overlays(sx, sy, text_renderer, window_controller)


    # Process manager and all widgets
    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing
        results = EventQueue()


        # Assume we didn't process the mouse, at first
        self.processed_mouse = False

        # We derive an initial masked value from the parameters in case
        # an object such as a dialog box is calling this locally in a
        # temporary GUI manager nad has already been masked.
        masked = masked

        # Track whether or not the user clicked the mouse somewhere on the screen (before processing any widget)
        pre_clicked = mouse["clicked"]

        # Process in reverse order (i.e. highest displayed gets input preference)
        for i in range( len(self.widget_order) - 1, -1, -1 ):

            # Convenience
            (name, widget) = (
                self.widget_order[i],
                self.get_widget_by_name( self.widget_order[i] )
            )

            # Might as well validate
            if (widget):

                # A click event deactivates any text box (or whatever).
                # If we clicked on it again, it'll remain active anyway...
                if (pre_clicked):

                    # Deactivate widget
                    widget.deactivate()


                # Only process visible widgets
                if (widget.alpha_controller.get_interval() > 0 or widget.alpha_controller.get_target() > 0):

                    results.append(
                        widget.process(sx, sy, text_renderer, control_center, masked = masked, system_input = system_input, mouse = mouse)
                    )

                    # Update masked flag; did the given widget process the mouse?
                    if ( widget.performed_mouse_processing() ):

                        # Set flag
                        masked = True

                        # Mark as having the mouse
                        self.processed_mouse = True

                        # If this widget possesses the mouse cursor at its current location, then no widget
                        # beneath this one can possibly respond to mouse clicks.
                        mouse["clicked"] = False

                # If the widget should not be processed, then it cannot have mouse focus
                else:

                    # Mark entire widget as not having performed mouse processing "last time" or "this time"
                    widget.processed_mouse_last_time = False
                    widget.processed_mouse = False


        # Return resultant events
        return results


    # Add an event manually (e.g. hotkey)
    def add_event(self, event):

        # Append
        self.pending_events.inject_event(event)


    # Return any events that need to take place
    def fetch_events(self):

        return self.pending_events

        events = copy.deepcopy(self.pending_events)

        self.pending_events = EventQueue()
        #events.extend(self.pending_events)
        # Now clear all of those pending events...
        #self.pending_events = []

        return events


    def create_dialog_from_xml_node(self, node, control_center):

        params = {}

        # Establish default values
        for key in self.gui_defaults["generic"]:
            params[key] = eval( self.gui_defaults["generic"][key] )

        # Use the specified values whenever possible
        for key in node.attributes:

            if (key in self.gui_defaults["generic"]):
                params[key] = eval( node.get_attribute(key) )


        dialog = Dialog(
            node.get_attribute("x"),
            node.get_attribute("y"),
            node.get_attribute("width"),
            node.get_attribute("height"),
            root = True
        ).configure({
            "name": node.get_attribute("name"),
            "max-width": SCREEN_WIDTH,
            "max-height": SCREEN_HEIGHT
        }).configure(
            node.get_attributes()
        )

        dialog.css(
            node.get_attributes()
        )

        dialog.z_index = 100

        # Get all of the dialog's children...
        child_collection = node.get_nodes_by_tag("*")

        for ref_child in child_collection:

            child_name = "untitled%d" % (1 + len(dialog.gui_manager.widgets))

            if (ref_child.get_attribute("name")):
                child_name = ref_child.get_attribute("name")

            elem = self.create_gui_element_from_xml_node(ref_child, dialog, control_center)

            if (elem != None):

                if ( ref_child.has_attribute("name") ):

                    elem.set_name(
                        ref_child.get_attribute("name")
                    )

                #dialog.add_element(child_name, elem)
                dialog.add_widget(elem)


        # Get any onload event
        for ref_onload in node.get_nodes_by_tag("onload"):

            dialog.hook(
                "load",
                EventQueueIter(
                    ref_onload.get_attribute("event"),
                    ref_onload.get_attributes()
                )
            )


        # Get any on-show event
        for ref_onshow in node.get_nodes_by_tag("onshow"):

            dialog.hook(
                "show",
                EventQueueIter(
                    ref_onshow.get_attribute("event"),
                    ref_onshow.get_attributes()
                )
            )


        # Get any mouseover event
        for ref_onmouseover in node.get_nodes_by_tag("onmouseover"):

            dialog.hook(
                "mouseover",
                EventQueueIter(
                    ref_onmouseover.get_attribute("event"),
                    ref_onmouseover.get_attributes()
                )
            )


        # Get any mouseout event
        for ref_onmouseout in node.get_nodes_by_tag("onmouseout"):

            dialog.hook(
                "mouseout",
                EventQueueIter(
                    ref_onmouseout.get_attribute("event"),
                    ref_onmouseout.get_attributes()
                )
            )


        # Get any on-submit event
        for ref_onsubmit in node.get_nodes_by_tag("onsubmit"):

            dialog.hook(
                "submit",
                EventQueueIter(
                    ref_onsubmit.get_attribute("event"),
                    ref_onsubmit.get_attributes()
                )
            )


        # Get any on-escape event
        for ref_onescape in node.get_nodes_by_tag("onescape"):

            dialog.hook(
                "escape",
                EventQueueIter(
                    ref_onescape.get_attribute("event"),
                    ref_onescape.get_attributes()
                )
            )


        dialog.__std_update_css__(control_center, universe = None) # (?) no universe needed?

        dialog.show()

        return dialog


    def create_gui_element_from_xml_node(self, node, parent, control_center):

        #save_replay_dialog.add_element("n/a", Label("Save as:", (10, 10), text_color = (255, 255, 255)))

        # Convenience
        text_renderer = control_center.get_window_controller().get_text_controller_by_name("gui").get_text_renderer()


        params = {}

        # Establish default values
        for key in self.gui_defaults["generic"]:
            params[key] = eval( self.gui_defaults["generic"][key] )

        # Some elements override those defaults with their own defaults
        if (node.tag_type in self.gui_defaults):

            for key in self.gui_defaults[node.tag_type]:
                params[key] = eval( self.gui_defaults[node.tag_type][key] )

        # Use the specified values whenever possible
        for key in node.attributes:

            if (key in self.gui_defaults["generic"]):
                params[key] = eval( node.get_attribute(key) )


        (x, y) = (0, 0)

        if ( node.get_attribute("x") ):

            x = node.get_attribute("x")

            if (len(x) > 0):

                # Percentage-based x?
                if (x[-1] == "%"):
                    percent = int( x[0 : len(x)-1] ) / 100.0

                    x = int(percent * parent.get_width())

                # Raw width
                else:
                    x = int(x)

            else:
                x = 0

        if ( node.get_attribute("y") ):

            y = node.get_attribute("y")

            if (len(y) > 0):

                # Percentage-based y?
                if (y[-1] == "%"):
                    percent = int( y[0 : len(y)-1] ) / 100.0

                    y = int(percent * parent.get_height(text_renderer))

                # Raw y
                else:
                    y = int(y)

            else:
                y = 0


        (w, h) = ("100%", 0)

        if ( node.has_attribute("width") ):

            w = node.get_attribute("width")

            if (len(w) > 0):

                # Percentage-based width?
                if (w[-1] == "%"):
                    percent = int( w[0 : len(w)-1] ) / 100.0

                    w = int(percent * parent.get_width())

                # Raw width
                else:
                    w = int(w)


            else:
                w = 0

        if ( node.has_attribute("height") ):

            h = node.get_attribute("height")

            if (len(h) > 0):

                # Percentage-based height?
                if (h[-1] == "%"):
                    percent = int( h[0 : len(h)-1] ) / 100.0

                    h = int(percent * parent.get_height(text_renderer))

                # Raw height
                elif ( is_numeric(h) ):

                    h = int(h)

                else:
                    h = 0

            else:
                h = 0



        # Declare for scope
        elem = None


        """
        # Special alignment?
        if ( node.get_attribute("align") ):

            if (node.get_attribute("align") == "center"):
                x -= (w / 2)

            elif (node.get_attribute("align") == "right"):
                x -= w
        """


        # Element stack?
        if (node.tag_type == "stack"):

            elem = ElementStack(x, y, w).css(
                node.get_attributes()
            ).configure({
                "bloodline": parent.get_bloodline(),
                "max-width": parent.get_width()
            })

            # Get all of the stack items
            child_collection = node.get_nodes_by_tag("*")

            for ref_child in child_collection:

                child_name = ""

                if (ref_child.get_attribute("name")):
                    child_name = ref_child.get_attribute("name")

                elem2 = self.create_gui_element_from_xml_node(ref_child, elem, control_center)

                if (elem2 != None):

                    if ( ref_child.has_attribute("name") ):

                        elem2.set_name(
                            ref_child.get_attribute("name")
                        )

                    elem.add_widget(elem2)

                    elem2.__std_update_css__(control_center, universe = None) # (?) no universe needed?

            elem.invalidate_cached_metrics()

        # Generic label
        elif (node.tag_type == "label"):

            elem = Label(
                node.get_attribute("value"),
                x,
                y,
                align = "%s" % node.get_attribute("align")
            )

            elem.set_text(node.get_attribute("value"), text_renderer)

        # Text entry
        elif (node.tag_type == "entry"):

            elem = Text_Box(x, y, w, h)

        # Dropdown
        elif (node.tag_type == "dropdown"):

            elem = Dropdown(x, y, w, h, int( node.get_attribute("numrows") ) )

            # Get default dropdown options
            option_collection = node.get_nodes_by_tag("option")

            for ref_option in option_collection:
                elem.add( "%s" % ref_option.get_attribute("title"), "%s" % ref_option.get_attribute("value") )


            """
            # Get any beforechange event...
            beforechange_collection = node.get_nodes_by_tag("beforechange")

            for ref_beforechange in beforechange_collection:

                e = {
                    "action": "%s" % ref_beforechange.get_attribute("event"),
                    "target": None,
                    "param": None
                }

                if (ref_beforechange.get_attribute("target")):
                    e["target"] = ref_beforechange.get_attribute("target")

                if (ref_beforechange.get_attribute("param")):
                    e["param"] = ref_beforechange.get_attribute("param")

                elem.beforechange_events.append(e)
            """

            # Get any beforechange event...
            for ref_beforechange in node.get_nodes_by_tag("beforechange"):

                elem.hook(
                    "beforechange",
                    EventQueueIter(
                        ref_beforechange.get_attribute("event"),
                        ref_beforechange.get_attributes()
                    )
                )

            """
            for ref_onchange in onchange_collection:

                e = {
                    "action": "%s" % ref_onchange.get_attribute("event"),
                    "target": None,
                    "param": None
                }

                if (ref_onchange.get_attribute("target")):
                    e["target"] = ref_onchange.get_attribute("target")

                if (ref_onchange.get_attribute("param")):
                    e["param"] = ref_onchange.get_attribute("param")

                elem.onchange_events.append(e)
            """

        # Listbox
        elif (node.tag_type == "listbox"):

            elem = Listbox(x, y, w, h, int( node.get_attribute("numrows") ), on_click = node.get_attribute("on-click") ).configure(
                node.get_attributes()
            )

            # Get default dropdown options
            option_collection = node.get_nodes_by_tag("option")

            for ref_option in option_collection:

                # We can add separators to a listbox, they mix in with the actual items...
                if ( ref_option.has_attribute("separator") ):

                    elem.add_separator()

                else:

                    elem.add( "%s" % ref_option.get_attribute("title"), "%s" % ref_option.get_attribute("value") )


            # Get any beforeclick event
            beforeclick_collection = node.get_nodes_by_tag("beforeclick")

            for ref_beforeclick in beforeclick_collection:

                elem.hook(
                    "preclick",
                    EventQueueIter(
                        ref_beforeclick.get_attribute("event"),
                        ref_beforeclick.get_attributes()
                    )
                )



            # Get any onchange event...
            for ref_onchange in node.get_nodes_by_tag("onchange"):

                elem.hook(
                    "change",
                    EventQueueIter(
                        ref_onchange.get_attribute("event"),
                        ref_onchange.get_attributes()
                    )
                )


        # Button
        elif (node.tag_type == "button"):

            elem = Button("%s" % node.get_attribute("value"), x, y, w, h)


        # Checkbox
        elif (node.tag_type == "checkbox"):

            elem = Checkbox(x, y, w, h, on_click = node.get_attribute("on-click"))


        # Generic rectangle, used mostly as a separator
        elif (node.tag_type == "rect"):

            elem = Rectangle(x, y, w, h)


        # Hidden element for data tracking
        elif (node.tag_type == "hidden"):

            elem = Hidden(node.get_attribute("value"))


        # Sub-dialog
        elif (node.tag_type == "dialog"):

            elem = Dialog(x, y, w, h).css(
                node.get_attributes()
            ).configure({
                "bloodline": parent.get_bloodline(),
                "max-width": parent.get_width()
            })

            elem.z_index = 100

            # Get all of the dialog's children...
            child_collection = node.get_nodes_by_tag("*")

            for ref_child in child_collection:

                child_name = ""

                if (ref_child.get_attribute("name")):
                    child_name = ref_child.get_attribute("name")

                elem2 = self.create_gui_element_from_xml_node(ref_child, elem, control_center)

                if (elem2 != None):

                    if ( ref_child.has_attribute("name") ):

                        elem2.set_name(
                            ref_child.get_attribute("name")
                        )

                    elem.add_widget(elem2)

                    elem2.__std_update_css__(control_center, universe = None) # (?) no universe needed?

            elem.invalidate_cached_metrics()


        # Treeview
        elif (node.tag_type == "treeview"):

            elem = Treeview(x, y, w, h, row_height = int( params["row-height"] ), parent = parent)



        # Did we create a widget?
        if (elem):

            # Grab inline style settings
            elem.css(
                node.get_attributes()
            ).configure(
                node.get_attributes()
            ).configure({
                "max-width": parent.get_width(),
                "bloodline": parent.get_bloodline()
            })


            # Check for a child
            ref_child = node.find_node_by_tag("child")

            # Validate
            if (ref_child):

                # Create a child widget
                elem.child = self.create_gui_element_from_xml_node(ref_child.get_first_node_by_tag("*"), elem, control_center)


            elem.__std_update_css__(control_center, universe = None) # (?) no universe needed?

            z = 0
            try:
                if ( elem.text == "Universe Name:" ):
                    z = elem.get_box_height(text_renderer)
            except:
                pass


            # Get any onload event
            for ref_onload in node.get_nodes_by_tag("onload"):

                elem.hook(
                    "load",
                    EventQueueIter(
                        ref_onload.get_attribute("event"),
                        ref_onload.get_attributes()
                    )
                )

            # Get any mouseover event
            for ref_onmouseover in node.get_nodes_by_tag("onmouseover"):

                elem.hook(
                    "mouseover",
                    EventQueueIter(
                        ref_onmouseover.get_attribute("event"),
                        ref_onmouseover.get_attributes()
                    )
                )


            # Get any mouseout event
            for ref_onmouseout in node.get_nodes_by_tag("onmouseout"):

                elem.hook(
                    "mouseout",
                    EventQueueIter(
                        ref_onmouseout.get_attribute("event"),
                        ref_onmouseout.get_attributes()
                    )
                )


            # Get any onclick event...
            for ref_onclick in node.get_nodes_by_tag("onclick"):

                elem.hook(
                    "click",
                    EventQueueIter(
                        ref_onclick.get_attribute("event"),
                        ref_onclick.get_attributes()
                    )
                )


            # Get any onchange event...
            for ref_onchange in node.get_nodes_by_tag("onchange"):

                elem.hook(
                    "change",
                    EventQueueIter(
                        ref_onchange.get_attribute("event"),
                        ref_onchange.get_attributes()
                    )
                )


            # Get any on-submit event
            for ref_onsubmit in node.get_nodes_by_tag("onsubmit"):

                elem.hook(
                    "submit",
                    EventQueueIter(
                        ref_onsubmit.get_attribute("event"),
                        ref_onsubmit.get_attributes()
                    )
                )

            #elem.blur()

            # Return the new element
            return elem


        # I guess we had some invalid markup
        else:

            return None

# Element is the base class for a GUI element; it has color properties,
# show/hide methods, and things like that; all elements will have these properties.
class Element(Widget):

    def __init__(self, selector, x, y, width = "100%", height = 0):

        Widget.__init__(self, selector)

        # Widget name (optional)
        self.name = ""

        # Widget parent (optional, typically unused)
        self.parent = None


        # Track whether we've run onload logic for this widget
        self.loaded = False


        # Visibility
        self.visible = True

        # Active widget?
        self.active = False

        # (?)
        self.z_index = 0

        # Coordinates
        self.x = x
        self.y = y

        # Last known render point
        self.last_render_x = x
        self.last_render_y = y


        # Alignment
        self.align = "left"
        self.valign = "top"


        # Dimensions
        self.width = width
        self.height = height



        # Some widgets might point to a child widget (e.g. buttons with submenus)
        self.child = None

        # (?) keep this?
        self.pending_events = []


        # Any widget can hook to a series of user actions, such as mouseover, click, etc.
        # By default, a widget does nothing when these things happen.
        self.hooks = {
            "mouseover": {},    # Each time we add a hook, we also give the hook a name.
            "mouseout": {},     # This will allow us to remove specific hooks, if we ever want to.
            "preclick": {},
            "click": {},
            "beforechange": {},
            "change": {},
            "load": {},
            "show": {},
            "submit": {},       # Used only by the text areas probably, I think (?) (i.e. press enter on active field to submit)
            "escape": {}        # This one will probably only be used by root-level dialogs... probably...
        }

        self.hook_orders = {} # We'll add in the action key on-the-fly


        # Each time we process a widget, we'll track whether or not it did anything with the mouse.
        # Once some widget has processed the mouse, no other widget should respond to mouse input.
        self.processed_mouse = False

        # We'll always keep track of whether we had processed the mouse in the /previous/ processing call.
        # This allows us to determine mouseover / mouseout events.
        self.processed_mouse_last_time = False


    # Configure
    def configure(self, options):

        # Generic Widget configure
        Widget.configure(self, options)


        if ( "name" in options ):
            self.name = options["name"]

        if ( "align" in options ):
            self.align = options["align"]

        if ( "valign" in options ):
            self.valign = options["valign"]


        # For chaining
        return self


    # Get widget name
    def get_name(self):

        return self.name


    # Set widget name
    def set_name(self, name):

        self.name = name


    # By default, an element will not search tiself for a child widget.  Overwrite as necessary (e.g. stack, dialog)
    def find_widget_by_name(self, name):

        return None


    # by default, an element will not find any widgets of a given selector within itself.  Some widget types will overwrite this function.
    def find_widgets_by_selector(self, selector):

        return []


    def fetch_events(self, alias = None):
        events = []
        events.extend(self.pending_events)

        for e in events:
            e["parent"] = alias

        self.pending_events = []

        return events


    # Set coordinates
    def set_coords(self, x, y):

        # Sure
        self.x = x
        self.y = y


    #def process(self, remove = 0, me = 0, later = 0, masked = 0, system_input = {}, mouse = {}, text_renderer = None, p_offset = None, parent = None):
    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Standard Widget processing
        results = Widget.__std_process__(self, control_center, universe = None) # (?) No universe needed?


        # Before resetting the processed mouse flag, let's remember its current setting (i.e. from last process call)
        self.processed_mouse_last_time = self.processed_mouse

        # Always assume a widget does not have the mouse.
        self.processed_mouse = False


        # Return standard processing events
        return results


    # Default method.  Overwrite as needed.
    def activate(self):

        return


    # Default method.  Overwrite as needed.
    def deactivate(self):

        return


    # Default method.  Overwrite as needed.
    def reset(self):

        return


    # Overwrite these when necessary ############
    def get_width(self):

        return Widget.get_width(self)


    def get_height(self, text_renderer):

        return Widget.get_height(self, text_renderer)


    # Report the widget's height.  Some widgets will overwrite this.
    def report_widget_height(self, text_renderer):

        #print self.height
        return self.get_height(text_renderer)


    # Get widget area
    def get_rect(self):

        return ( self.get_x(), self.get_y(), self.get_width(), self.get_height() )


    # Get visible (?) widget height
    def get_visible_height(self):

        return self.height
    #############################################

    """
    def show(self):
        self.visible = True

        if (self.child):
            self.child.show()

    def hide(self):
        self.visible = False

        if (self.child):
            self.child.hide()
    """

    def is_visible(self):
        return self.visible


    # See if a widget performed mouse processing
    def performed_mouse_processing(self):

        # Check flag
        return self.processed_mouse


    def has_mouse(self, sx, sy):
        self_has_mouse = self.is_visible() and intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height()) )
        child_has_mouse = False

        if (self.child):
            child_has_mouse = self.child.is_visible() and self.child.has_mouse((0, 0))# (self.get_width() + sx, sy) )

        return (self_has_mouse or child_has_mouse)


    # Hook into a widget event, providing a callback to call in response to the action
    def hook_with_name(self, hook, name, callback):

        # Validate hook name
        if (hook in self.hooks):

            # Initialize the order list for this hook if we haven't already
            if ( not (hook in self.hook_orders) ):

                # Order matters, sometimes...
                self.hook_orders[hook] = []


            # Make sure a hook by this name does not already exist
            if ( not (name in self.hooks[hook]) ):

                # Add hook
                self.hooks[hook][name] = callback

                # Remember the order
                self.hook_orders[hook].append(name)

            else:
                log( "Warning:  Hook named '%s' already exists in hook name '%s!'" % (name, hook) )

        else:
            log( "Warning:  Hook name '%s' does not exist!" % hook )


    # Hook with no given name; it'll generate a random name, and we basically cannot ever remove this hook.
    def hook(self, hook, callback):

        # Validate hook name
        if (hook in self.hooks):

            # Generate a random hook name; function automatically avoids duplicates
            name = self.generate_unique_random_hook_name()

            # Hook by (random) name
            self.hook_with_name(hook, name, callback)

        else:
            log( "Warning:  Hook name '%s' does not exist!" % hook )


    # Generate a random hook name
    def generate_unique_random_hook_name(self):

        # PIck a random number, basically
        name = "generic.%d" % random.randint(1, 10000)

        # Keep trying in case we have duplicates
        while ( any( (name in self.hooks[action]) for action in self.hooks ) ):

            # Try again
            name = "generic.%d" % random.randint(1, 10000)

        # Return random name
        return name


    # Raise an action (e.g. mouseover, click, etc.)
    def raise_action(self, action):

        # Track results
        results = EventQueue()

        # Check to see if we track hooks for the given action (i.e. validate)
        if (action in self.hooks):

            # See if we've added any hook for this event yet
            if ( len( self.hooks[action] ) > 0 ):

                # Loop through each named hook, in the order we added them...
                for name in self.hook_orders[action]:

                    # Add resultant events
                    results.inject_event(
                        self.hooks[action][name]
                    )

        # Return events
        return results


    # Most widgets won't use this, but this function allows us to render
    # "overlays" such as a dropdown's dropdown box in a 2nd pass, on top of any lower widgets.
    def render_overlays(self, sx, sy, text_renderer, window_controller):

        pass


# A generic element stack, whose only purpose is to render other elements
class ElementStack(Element):

    def __init__(self, x, y, width):

        Element.__init__(self, "stack2", x, y, width, 0)


        # Stack items
        self.widgets = []

        # We can instruct a "stack" to display its contents in an inline list instead of a block list
        self.inline = False


        # We can specify a minimum height for the stack
        self.min_height = None

        # We can also specify a maximum height for the stack
        self.max_height = None

        # If the contents exceed a given maximum height, then we'll need a scrollbar
        self.scrollbar = Scrollbar(0, 0, 6, 0, step = 25).configure({
            "bloodline": self.get_bloodline()
        })


    # Configure
    def configure(self, options):

        # Standard Element configure
        Element.configure(self, options)


        if ( "inline" in options ):
            self.inline = ( int( options["inline"] ) == 1 )

        if ( "min-height" in options ):
            self.min_height = int( options["min-height"] )

        if ( "max-height" in options ):
            self.max_height = int( options["max-height"] )


        # For chaining
        return self


    # Overwrite
    def configure_alpha_controller(self, options):

        # Standard configuration
        Widget.configure_alpha_controller(self, options)

        # Forward to children
        for widget in self.widgets:

            # Cascade
            widget.configure_alpha_controller(options)


    # A stack's height is equal to the height required to render each widget in the stack
    def report_widget_height(self, text_renderer):

        if (self.inline):

            return max( ( widget.get_y() + widget.get_box_height(text_renderer) ) for widget in self.widgets )

        else:

            if (self.max_height):

                return self.max_height

            else:

                return sum( ( widget.get_y() + widget.get_box_height(text_renderer) ) for widget in self.widgets )


    # Forward updated css state to list elements on focus
    def on_focus(self):

        # Update scrollbar's bloodline
        self.scrollbar.configure({
            "bloodline": self.get_bloodline()
        })

        # Loop widgets
        for widget in self.widgets:

            # Update bloodline for children
            widget.css({
                "bloodline": self.get_bloodline()
            })

            widget.on_focus()


    # Forward updated css state to list elements on blur
    def on_blur(self):

        # Update scrollbar's bloodline
        self.scrollbar.configure({
            "bloodline": self.get_bloodline()
        })

        # Loop widgets
        for widget in self.widgets:

            # Update each child's bloodline
            widget.css({
                "bloodline": self.get_bloodline()
            })

            widget.on_blur()


    def on_show(self, target, animated, on_complete):

        for widget in self.widgets:

            widget.show(target, animated, on_complete)

    def on_hide(self, target, animated, on_complete):

        for widget in self.widgets:

            widget.hide(target, animated, on_complete)


    # Add a widget to the dialog
    def add_widget(self, widget):

        # New widget
        self.widgets.append(
            widget.css({
                "bloodline": self.get_bloodline()
            }).configure({
                "max-width": self.get_width()
            })
        )

        #self.widgets[-1].blur()


    # Something of a hacky redirect
    def get_widget_by_name(self, name):

        # Loop widgets
        for widget in self.widgets:

            # check widget name
            if ( widget.get_name() == name ):

                return widget

        # Couldn't find it
        return None


    # find a widget by a given name within this dialog
    def find_widget_by_name(self, name):

        # Loop widgets
        for widget in self.widgets:

            # Check this widget
            if ( widget.get_name() == name ):

                # Matched
                return widget

            # Search children, if possible
            else:

                # Let's see if we can find it nested
                nested_widget = widget.find_widget_by_name(name)

                # Result?
                if (nested_widget):

                    # We found the widget
                    return nested_widget


        # We couldn't find it...
        return None


    # Find all widgets of a given selector type
    def find_widgets_by_selector(self, selector):

        # Track matches
        matches = []

        # Loop widgets
        for widget in self.widgets:

            # Compare selector
            if ( widget.selector == selector ):

                # Match
                matches.append(widget)

            # Check for children, also...
            matches.extend(
                widget.find_widgets_by_selector(selector)
            )

        # Add in any matches for the widget child, if/a
        if (self.child):

            # Add matches
            matches.extend(
                self.child.find_widgets_by_selector(selector)
            )


        # Return matches
        return matches


    # Get all elements of a given selector type
    def get_elements_by_selector(self, selector):

        # Track matches
        results = []

        # Loop widgets
        for widget in self.widgets:

            # Match?
            if (widget.selector == selector):

                # Add to results
                results.append(widget)

        # Return matches
        return results



    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Standard element processing
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)


        # Default offset
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )


        # X align center?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx -= self.get_width()


        # Y align center?
        if (self.valign == "center"):

            ry -= int( self.report_widget_height(text_renderer) / 2 )

        # Y align bottom?
        elif (self.valign == "bottom"):

            ry -= self.report_widget_height(text_renderer)


        # Update mouse processing flag for overall stack
        self.processed_mouse = ( not masked ) and ( intersect( (rx, ry, self.get_width(), self.get_render_height(text_renderer)), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), quick = True ) )


        # Factor in padding as we prepare to render child widgets
        rx += self.get_padding_left()
        ry += self.get_padding_top()


        # Hack in scrollbar offset factoring
        scrollbar_offset = 0

        # Do we need it?
        if (self.scrollbar.height > 0):

            # Offset by current scrollbar value
            scrollbar_offset = self.scrollbar.get_value()


        # Process scrollbar if it's visible (i.e. needed)
        if (self.scrollbar.height > 0):

            results.append(
                self.scrollbar.process(sx + self.get_x() + self.get_width() - self.scrollbar.get_width(), sy, text_renderer, control_center, masked, system_input, mouse, parent)
            )

            # Check for mouse wheel scroll on the general stack area
            if (self.processed_mouse):

                # Scroll down?
                if (mouse["scrolled"] == "down"):

                    # Step the scrollbar, down
                    self.scrollbar.step_down()

                # Scroll up?
                elif (mouse["scrolled"] == "up"):

                    # Step the scrollbar, up
                    self.scrollbar.step_up()


        # Process each stack item
        for widget in self.widgets:

            results.append(
                widget.process(rx, ry - scrollbar_offset, text_renderer, control_center, masked = masked, system_input = system_input, mouse = mouse)
            )

            # Update masked flag; did this widget process the mouse?
            masked |= widget.performed_mouse_processing()

            # If the widget exceeds the reported size of the stack (e.g. dropdowns), we'll still count the dialog as having the mouse if the mouse intersects the overflow
            self.processed_mouse |= widget.performed_mouse_processing()

            if (self.inline):

                rx += widget.report_widget_width(text_renderer) + (widget.get_padding_left() + widget.get_padding_right())

            else:

                # Advance processing cursor
                ry += widget.get_box_height(text_renderer)



        if (self.processed_mouse):

            # If not last time, focus and raise mouseover action
            if (not self.processed_mouse_last_time):

                # Focus
                self.focus()

                # Raise mouseover action
                results.append(
                    self.raise_action("mouseover")
                )

        else:

            # If we had the mouse last time, blur and raise mouseout action
            if (self.processed_mouse_last_time):

                # Blur
                self.blur()

                # Raise mouseout action
                results.append(
                    self.raise_action("mouseout")
                )

        return results


    # Render dialog and child widgets
    def draw(self, sx, sy, text_renderer, window_controller):

        # Rendering position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left(),
            sy + self.get_y() + self.get_padding_top()
        )

        (ox, oy) = (rx, ry)


        # X align center?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx -= self.get_width()


        # Y align center?
        if (self.valign == "center"):

            ry -= int( self.report_widget_height(text_renderer) / 2 )

        # Y align bottom?
        elif (self.valign == "bottom"):

            ry -= self.report_widget_height(text_renderer)


        if (self.max_height):

            Widget.__std_render_border__( self, rx, ry, self.get_width(), self.max_height, window_controller, rounded = False )#self.get_has_rounded_corners() )

            # Scissor on max height
            window_controller.get_scissor_controller().push(
                (rx, ry, self.get_width(), self.max_height)
            )


        # Hack in scrollbar offset factoring
        scrollbar_offset = 0

        # Do we need it?
        if (self.scrollbar.height > 0):

            # Offset by current scrollbar value
            scrollbar_offset = self.scrollbar.get_value()


        # Render each item
        for widget in self.widgets:

            widget.draw(rx, ry - scrollbar_offset, text_renderer, window_controller)

            if (self.inline):

                rx += widget.report_widget_width(text_renderer) + (widget.get_padding_left() + widget.get_padding_right())

            else:

                # Advance cursor
                ry += widget.get_box_height(text_renderer)

            #draw_rect( sx + self.get_x() + widget.x, sy + self.get_y() + widget.y, widget.width, widget.report_widget_height(text_renderer), (225, 225, 25, 0.15) )


        # If we're using a max height and the length of the contents exceeds the max height, let's draw a scrollbar
        if (self.max_height):

            #print (ry - oy), self.max_height

            if ( (ry - oy) > self.max_height ):

                # What a hack job!
                self.scrollbar.height = self.max_height

                # The max scroll amount equals the amount by which we exceed the maximum height
                self.scrollbar.max_value = ( (ry - oy) - self.max_height )


                # Render scrollbar
                self.scrollbar.draw(rx + self.get_width() - self.scrollbar.get_width(), oy, text_renderer, window_controller)

            else:
                self.scrollbar.height = 0


        # Undo scissor if we are using a max height
        if (self.max_height):

            window_controller.get_scissor_controller().pop()


        #draw_rect_frame( sx + self.get_x(), sy + self.get_y(), self.width, self.report_widget_height(text_renderer), (225, 25, 25, 0.5), 2 )
        """
        if (self.processed_mouse):
            draw_rect(ox, oy, self.width, self.get_box_height(text_renderer), (225, 25, 25, 0.15))
        else:
            draw_rect(ox, oy, self.width, self.get_box_height(text_renderer), (225, 225, 25, 0.15))
        """

    # Stack forwards this call to its widgets
    def render_overlays(self, sx, sy, text_renderer, window_controller):

        # Rendering position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left(),
            sy + self.get_y() + self.get_padding_top()
        )

        (ox, oy) = (rx, ry)


        # X align center?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx -= self.get_width()


        # Y align center?
        if (self.valign == "center"):

            ry -= int( self.report_widget_height(text_renderer) / 2 )

        # Y align bottom?
        elif (self.valign == "bottom"):

            ry -= self.report_widget_height(text_renderer)


        # Render each widget's overlays
        for widget in self.widgets:

            widget.render_overlays(rx, ry, text_renderer, window_controller)

            # Advance cursor
            ry += widget.get_box_height(text_renderer)



class Slider(Element):

    def __init__(self, text, x, y, width, height, min_value = 0, max_value = 100, step = 1, on_change = None):

        Element.__init__(self, "slider", x, y, width, height)


        # Track the label for this slider
        self.text = text

        # Default to max value (?)
        self.value = max_value

        # ** hard-coded shade (?)
        self.shade = (0, 100, 0)

        # Track range
        self.min_value = min_value
        self.max_value = max_value

        # How many increments to step when ... (?)
        self.step = step

        # (?)
        self.show_markers = False

        # (?)
        self.on_change = p_on_change



    # Update label
    def set_text(self, text):

        self.text = text


    # Get current value
    def get_value(self):

        return self.value


    # Set current value
    def set_value(self, p_value):

        # Check to see if it's changing
        if (self.value != p_value):

            # Update
            self.value = p_value

            # Callback?
            if (self.on_change):

                # I guess we can have multiple callbacks, dumb
                for f in self.on_change:

                    # Run each callback
                    f()


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing this slider
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        self.active = 0

        # Let's see if we're hovering on the slider...
        pos_mouse = pygame.mouse.get_pos()

        result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_render_height(text_renderer)) )
        if (result and (not masked)):

            self.active = 1

            if (pygame.mouse.get_pressed()[0]):
                offset_x = pos_mouse[0] - (self.get_x() + sx)

                new_value = int( ((1.0 * offset_x) / (1.0 * self.get_width())) * self.max_value)

                # Round to the nearest multiple (perhaps the slider can only have values of 0, 5, 10, 15, and 20).
                # Add the multiple definition, then divide and multiply to emulate rounding.
                self.set_value( ( (new_value + self.step) / self.step) * self.step )

            #return True

        else:
            self.active = 0

            #return False

        # Return events
        return results


    # Render slider
    def draw(self, sx, sy, text_renderer, window_controller):

        # How far has the user moved the slider?
        percent = int( ((1.0 * self.value) / (1.0 * self.max_value)) * self.get_width())

        draw_rect(self.get_x() + sx, self.get_y() + sy, self.get_width(), self.get_render_height(text_renderer), self.background)
        draw_rect(self.get_x() + sx, self.get_y() + sy, percent, self.get_render_height(text_renderer), self.shade)
        draw_rect_frame(self.get_x() + sx, self.get_y() + sy, self.get_width(), self.get_render_height(text_renderer), self.border_color, 2)

        if (len(self.text) > 0):
            text_renderer.render_with_wrap(self.text, (self.get_x() + sx) + (self.get_width() / 2), (self.get_y() + sy), (255, 255, 255), align = "center")

        if (self.show_markers):
            for i in range(self.min_value, self.max_value + self.step, self.step):
                bar_width = (self.get_width() / ((self.max_value - self.min_value + self.step) / self.step))
                x_offset = ((i - self.min_value) / self.step) * bar_width

                draw_rect(sx + self.get_x() + x_offset, sy + self.get_y(), 1, self.get_render_height(text_renderer), (255, 255, 255))
                text_renderer.render_with_wrap("%d" % i, sx + self.get_x() + x_offset + (bar_width / 2), sy + self.get_y() - 25, (255, 255, 255), align = "center")


class Scrollbar(Element):

    def __init__(self, x, y, width, height, min_value = 0, max_value = 10, step = 1):
                                                  #p_on_change=None, p_listener=None, 

        Element.__init__(self, "scrollbar", x, y, width, height)


        # Default to minimum scroll
        self.value = min_value

        # Hard-coded (?)
        self.scrollbar_color = (200, 200, 200)

        # Track range
        self.min_value = min_value
        self.max_value = max_value

        # Track step
        self.step = step

        # On-change collection (?)
        self.on_change = []#p_on_change

        #self.listener = p_listener


    # Check current position value
    def get_value(self):

        return self.value


    # Set current position value
    def set_value(self, value):

        # Is it changing?
        if (self.value != value):

            # Update
            self.value = value


            # Check on-change collection
            if (self.on_change):

                # Loop all
                for f in self.on_change:

                    # Callback
                    f()


    # Scorll down by one increment
    def step_down(self):

        # As long as there's scrolling to be done...
        if (self.value < self.max_value):

            # Increment by one step
            self.value += self.step

            # Don't overshoot
            if (self.value > self.max_value):

                # Clamp
                self.value = self.max_value


            # Check on-change collection
            if (self.on_change):

                # Loop all
                for f in self.on_change:

                    # Callback
                    f()


    # Scroll up by one increment
    def step_up(self):

        # As long as we've scrolled down some...
        if (self.value > self.min_value):

            # One step at a time!
            self.value -= self.step

            # Don't overshoot
            if (self.value < self.min_value):

                # Clamp
                self.value = self.min_value


            # Check on-change collection
            if (self.on_change):

                # Loop all
                for f in self.on_change:

                    # Callback
                    f()


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing scrollbar
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        self.active = 0

        #if (self.listener):
        #    self.max_value = self.listener()

        # Let's see if we're hovering on the slider...
        pos_mouse = pygame.mouse.get_pos()

        if ( (not masked) and ( intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_render_height(text_renderer)) ) ) ):

            # Flag as having mouse
            self.processed_mouse = True

            # If not last time, give it focus
            if (not self.processed_mouse_last_time):

                # Focus!
                self.focus()

            if (pygame.mouse.get_pressed()[0]):

                #print self.min_value, self.max_value, self.step
                # I don't want the scroll smaller than 12 pixels tall

                if (self.max_value > self.min_value):

                    scrollbar_size = max(12, int(self.get_render_height(text_renderer) / ( (self.max_value - self.min_value) / self.step)))

                    offset_y = pos_mouse[1] - (self.get_y() + sy)
                    new_value = int( (float(offset_y) / float(self.get_render_height(text_renderer))) * (self.max_value - self.min_value))

                    if (offset_y < 12):
                        new_value = 0
                    elif (self.get_render_height(text_renderer) - offset_y < 12):
                        new_value = self.max_value

                    # Round to the nearest multiple (perhaps the slider can only have values of 0, 5, 10, 15, and 20).
                    # Add the multiple definition, then divide and multiply to emulate rounding.
                    #self.set_value( ( (new_value + self.step) / self.step) * self.step )
                    self.set_value(new_value)

                else:

                    self.set_value(self.min_value)

        else:

            # Flag as not having mouse
            self.processed_mouse = False

            # If we had the mouse last time, we should blur
            if (self.processed_mouse_last_time):

                # Blur widget
                self.blur()


        # Return resultant events
        return results


    # Render scrollbar
    def draw(self, sx, sy, text_renderer, window_controller):

        render_height = self.get_render_height(text_renderer)

        # I don't want the scroll smaller than 12 pixels tall
        scrollbar_size = render_height

        if (self.max_value - self.min_value > 0):
            try:
                scrollbar_size = max(36, int(render_height / ( (self.max_value - self.min_value) / self.step)))
            except:
                scrollbar_size = 36

            draw_rect(self.get_x() + sx, self.get_y() + sy, self.get_width(), render_height, self.get_gradient_start())
            draw_rect(self.get_x() + sx, max(self.get_y() + sy, self.get_y() + sy + 12 + ( float(self.get_value() / float(self.max_value)) * (render_height - 12)) - scrollbar_size), self.get_width(), scrollbar_size, self.get_color())
            draw_rect_frame(self.get_x() + sx, self.get_y() + sy, self.get_width(), render_height, self.get_border_color(), self.get_border_size())

        else:
            draw_rect(self.get_x() + sx, self.get_y() + sy, self.get_width(), render_height, self.get_gradient_start())
            draw_rect(self.get_x() + sx, max(self.get_y() + sy, self.get_y() + sy + 12 + ( 0 * (render_height - 12)) - scrollbar_size), self.get_width(), scrollbar_size, self.get_color())
            draw_rect_frame(self.get_x() + sx, self.get_y() + sy, self.get_width(), render_height, self.get_border_color(), self.get_border_size())

        if (self.active):

            # Draw a border to highlight the fact that there's a mouseover
            draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), render_height, (0.5, 0.5, 0.5), 1)

        #text_renderer.render_with_wrap(self.get_bloodline(), 5, 5, (225, 225, 25))


class Checkbox(Element):

    def __init__(self, x, y, width, height, on_click):

        Element.__init__(self, "checkbox", x, y, width, height)


        # Default to not checked
        self.checked = False

        # Event to fire when clicked
        self.on_click = on_click

        # We can make a checkbox "readonly."  If we do this, we can still check/uncheck it programmatically.
        self.readonly = False


    # Report widget height
    #def report_widget_height(self, text_renderer):
    #    return self.


    # Configure
    def configure(self, options):

        # Stnadard Element configure
        Element.configure(self, options)


        if ( "checked" in options ):
            self.checked = ( int( options["checked"] ) == 1 )

        if ( "readonly" in options ):
            self.readonly = ( int( options["readonly"] ) == 1 )


        # For chaining
        return self


    # Check the checkbox
    def check(self):

        # Events that result from checking the checkbox
        results = EventQueue()

        # Mark as checked
        self.checked = True

        # Add on-click event
        results.inject_event(
            EventQueueIter(
                self.on_click,                      # The event to fire
                {
                    "checked": self.checked         # This checkbox's status
                }
            )
        )

        # Return events
        return results


    # Uncheck the checkbox
    def uncheck(self):

        # Events that result from checking the checkbox
        results = EventQueue()

        # Mark as checked
        self.checked = False

        # Add on-click event
        results.inject_event(
            EventQueueIter(
                self.on_click,                      # The event to fire
                {
                    "checked": self.checked         # This checkbox's status
                }
            )
        )

        # Return events
        return results


    # Toggle the checkbox
    def toggle(self):

        # Events that result from checking the checkbox
        results = EventQueue()

        # Toggle checked status
        self.checked = (not self.checked)

        # Add on-click event
        results.inject_event(
            EventQueueIter(
                self.on_click,                      # The event to fire
                {
                    "checked": self.checked         # This checkbox's status
                }
            )
        )

        # Return events
        return results


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing checkbox

        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        #print self.height, self.max_height, self.get_render_height(text_renderer)


        self.active = 0

        pos_mouse = pygame.mouse.get_pos()

        # If this isn't a readonly checkbox, then check for user mouse click
        if (not self.readonly):

            # Check intersection result
            result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_render_height(text_renderer)) )

            # Is the mouse hovering over the checkbox?
            if (result and (not masked)):

                # Click detected?
                if (mouse["clicked"]):

                    # Toggle checkbox
                    self.checked = (not self.checked)

                    #if (self.on_click):
                    #    for f in self.on_click:
                    #        f()

                    # Always add in a custom event based on this checkbox's on-click event
                    results.inject_event(
                        EventQueueIter(
                            self.on_click,                      # The event to fire
                            {
                                "checked": self.checked         # This checkbox's status
                            }
                        )
                    )


        # Return resultant events
        return results


    # Render the checkbox
    def draw(self, sx, sy, text_renderer, window_controller):

        # Convenience
        alpha = self.get_background_alpha() * self.alpha_controller.get_interval()

        # Render position
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )

        # Render border.  Never round corners for a checkbox
        Widget.__std_render_border__( self, rx, ry, self.get_width(), self.get_render_height(text_renderer), window_controller, rounded = False )

        """
        # Render backdrop
        draw_rect(
            sx + self.get_x(),
            sy + self.get_y(),
            self.get_width(),
            self.get_render_height(text_renderer),
            set_alpha_for_rgb( alpha, self.get_gradient_start() )
        )

        # Frame it
        draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_render_height(text_renderer), (255, 255, 255), 2)

        if (self.active):

            # Draw a border to highlight the fact that there's a mouseover
            draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.height, (255, 255, 0, 0.5), 1)

        if (self.checked):

            draw_rect(sx + self.get_x() + 2, sy + self.get_y() + 2, self.get_width() - 4, self.get_height() - 4, (255, 0, 0))
        """

        # Fill in the checkbox if it's checked...
        if (self.checked):

            # Padding for the fill 
            padding = 3

            # Fill size
            (width, height) = (
                self.get_width() - (2 * padding),
                self.get_render_height(text_renderer) - (2 * padding)
            )

            # Box within a box, using the border color
            draw_rect(
                sx + self.get_x() + padding,
                sy + self.get_y() + padding,
                width,
                height,
                set_alpha_for_rgb( alpha, self.get_border_color() )
            )


class Button(Element):

    def __init__(self, text, x, y, width, height):#, p_on_click=None, p_on_mouseover=None, p_on_mouseout=None, background=None, background_active=None, border_color=None, border_color_active=None, text_color=None, text_color_active=None, image=None, image_active=None, has_rounded_corners = True):

        Element.__init__(self, "button", x, y, width, height)

        # Button label
        self.text = text


        # (?) Return value
        self.value = ""

        # Track mouseover status
        self.moused_over = False

        self.params = {}


    # Report button height
    def report_widget_height(self, text_renderer):

        # Total hack job!
        if (self.css_class == "closer"):

            return 24

        else:

            return text_renderer.font_height


    # Change button label
    def set_text(self, text):

        self.text = text


    # Get button label
    def get_text(self):

        return self.text


    # Set child for this button (i.e. submenu widget)
    def set_child(self, child):

        self.child = child


    # Set value (?)
    def set_value(self, value):

        self.value = value


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        # Default cursor point
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )

        # X align center?
        if (self.align == "center"):

            rx = sx + self.get_x() - int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx = sx + self.get_x() - self.get_width()


        pos_mouse = pygame.mouse.get_pos()
        intersects_button = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (rx, ry, self.get_width(), self.get_render_height(text_renderer)) )

        #draw_rect( rx, ry, self.get_width(), self.get_render_height(text_renderer), (225, 225, 25, 0.15) )

        #print masked, pos_mouse, offset_rect( self.get_rect(), sx, sy )

        if ( (intersects_button) and (not masked) ):

            # Flag as having mouse
            self.processed_mouse = True

            # If not last time, update css state and raise mouseover action
            if (not self.processed_mouse_last_time):

                # Focus
                self.focus()

                # Raise mouseover action
                results.append(
                    self.raise_action("mouseover")
                )

            """
            if (len(self.onmouseover_events) > 0 and self.moused_over == 0):

                #for f in self.on_mouseover:
                #    f()

                for e in self.onmouseover_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": self.params
                    })

                self.moused_over = 1 # We'll reset this when we move the mouse away
            """

            if (intersects_button):

                self.active = True

                if (mouse["clicked"]):

                    results.append(
                        self.raise_action("click")
                    )

                    #if (self.on_click):
                    #    for f in self.on_click:
                    #        f()

                    #for f in self.onclick_functions:
                    #    f()
                    """
                    for e in self.onclick_events:

                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": self.params
                        })
                    """

            if (self.child):
                self.child.show()#visible = 1#show(text_renderer)
                self.child.set_coords(self.get_x() + sx + self.get_width(), self.get_y() + sy)

                if (self.child.coords[0] + self.child.get_width() > 640):# or intersect_any(self.child.get_rect(), self.blacklist)):
                    self.child.set_coords(self.get_x() + sx - self.child.get_width(), self.child.coords[1])

                if (self.child.coords[1] + self.child.get_height() > 480):
                    self.child.set_coords(self.child.coords[0], self.get_y() + sy - self.child.get_height() + self.get_height())

                self.child.process(text_renderer, control_center, (0, 0), masked, system_input, mouse)

            #return True # We tell the GUI handler not to process any lower objects

        else:

            # Flag as not having mouse
            self.processed_mouse = False

            # If we had it last time, then we should blur and raise the mouseout action
            if (self.processed_mouse_last_time):

                # Blur
                self.blur()

                # Raise mouseout action
                results.append(
                    self.raise_action("mouseout")
                )
                #if (self.on_mouseout):
                #    for f in self.on_mouseout:
                #        f()

            if (self.child):
                self.child.hide()

            #return False # The GUI handler is able to handle a lower object because it didn't handle this one

        # Return resultant events
        return results


    # Render button
    def draw(self, sx, sy, text_renderer, window_controller):

        #self.render_background(text_renderer, sx, sy)

        # Render point
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )

        # X align center?
        if (self.align == "center"):

            rx = sx + self.get_x() - int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx = sx + self.get_x() - self.get_width()



        # Render border
        Widget.__std_render_border__( self, rx, ry, self.get_width(), self.get_render_height(text_renderer), window_controller, rounded = self.get_has_rounded_corners() )


        # Render point for text
        (rxText, ryText) = (
            rx + self.get_padding_left(),
            ry + self.get_padding_top()
        )

        # Center align text?
        if (self.get_text_align() == "center"):

            # Adjust text render point
            rxText = rx + int(self.get_width() / 2)

        # Align text right?
        elif (self.get_text_align() == "right"):

            # All the way over
            rxText = rx + self.get_width()

        # Align text dead center?
        elif (self.get_text_align() == "origin"):

            rxText = rx + int(self.get_width() / 2) - int(text_renderer.size(self.text) / 2)
            ryText = ry + - self.get_padding_top() + int(self.get_render_height(text_renderer) / 2) - int(text_renderer.font_height / 2) - 4 # ** value - 4 is a hack


        # Fetch alpha interval
        alpha = self.alpha_controller.get_interval()


        text_renderer.render_with_wrap(self.text, rxText, ryText, set_alpha_for_rgb( alpha, self.get_color() ), self.get_width() - 2, align = self.get_text_align())

        if (0):
            #if (self.background):
            #    draw_rect(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height(), self.background)

            #if (self.image):
            #    self.image.draw(self.get_x() + sx, self.get_y() + sy, window_controller = window_controller)

            #if (self.border_color):
            #    draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height(), self.border_color, 1)

            #text_color = (225, 25, 25)
            #text_renderer.render_with_wrap(self.text, rxText, ryText, text_color, self.get_width() - 2, align = self.get_text_align())
            pass

        if (self.child):
            if (self.child.is_visible()):
                self.child.draw(where, text_renderer, (0, 0), window_controller = window_controller)


class Text_Box(Element):

    def __init__(self, x, y, width, height, rows = 1):

        Element.__init__(self, "input", x, y, width, height)

        # Track active text
        self.text = ""

        # We can flag the input field for redaction, clearing all existing text.  We check for this flag when processing...
        self.redacted = False


        # (?) I think we use these to track currently visible text
        self.text_visible = []
        self.rows = []

        self.editing = False

        self.center = False

        self.bounds = []
        self.row_bounds = [0, rows]

        # Height in rows
        self.num_rows = rows


        # Current count of the lines this text box uses
        self.total_rows = 0

        # Current row (?)
        self.current_row = 0


        # Track scrolling for multi-line text boxes
        self.scroll_point = 0


        # Cursor blink tracking
        self.blinking = False
        self.blink_wait = 0
        self.blink_wait_delay = 15


        # Each row has its own variable to track the visible text in that row.
        # Default to empty string for each potential row.
        for i in range(0, self.num_rows):

            # Also specify that each row points to no text data
            self.bounds.append([0, 0])

            # Empty string, pending input / change
            self.text_visible.append("")


        # Cursor tracking
        self.cursor_position = 0
        self.cursor_offset = 0 # For multi-line offset tracking

        self.x_offset = 0

        self.padding = 5

        self.formatted = False

        self.backspace_wait = 0
        self.left_arrow_wait = 0
        self.right_arrow_wait = 0
        self.return_wait = 0

        self.getter = None
        self.setter = None

    def deactivate(self):
        self.active = False
        self.editing = False

        # Flag as not having mouse
        self.processed_mouse = False

        self.blur()


    # Activate input field
    def activate(self):

        # Noe we're editing
        self.editing = True

        # Focus on widget
        self.focus()


    # Reset input field (i.e. reset text)
    def reset(self):

        # Kind of a hack.  Okay, totally a hack.  I don't want to have to pass text renderer et al. to this function, though!
        self.redacted = True


    # Overwrite
    def get_visible_height(self):
        return (self.height * self.num_rows)


    # Get current text
    def get_text(self):

        return self.text


    # Portal function
    def get_value(self):

        # This lets me call .get_value on a generic widget (e.g. dropdown, listbox, text entry...)
        return self.get_text()


    # Set current text
    def set_text(self, text, text_renderer):

        # Erase visible text trackers
        for i in range(0, self.num_rows):
            self.text_visible[i] = ""

        # Update text
        self.text = text

        # Compute row data
        self.rows = self.compute_rows(text_renderer)

        # Jump to the end of the text box
        self.move_cursor("end", text_renderer)


    def scroll_up(self, text_renderer):
        if (self.row_bounds[0] > 0):
            self.row_bounds[0] -= 1

            self.compute_rows(text_renderer)

    def scroll_down(self, text_renderer):
        if (self.row_bounds[0] + self.num_rows <= self.get_row_count(text_renderer)):
            self.row_bounds[0] += 1

            self.compute_rows(text_renderer)

    def scroll_to(self, row):
        self.scroll_point = row

        if (self.scroll_point < 0):
            self.scroll_point = 0

        if (self.scroll_point + (self.num_rows) >= len(self.rows)):
            self.scroll_point = max(0, len(self.rows) - self.num_rows)

        if (self.setter):
            self.setter(self.scroll_point)

    def scroll_to2(self, p_row, text_renderer):
        self.row_bounds[0] = p_row

        if (self.row_bounds[0] < 0):
            self.row_bounds[0] = 0

        elif (self.row_bounds[0] + self.num_rows >= self.total_rows):
            self.row_bounds[0] = self.total_rows - 1 - self.num_rows

        #self.compute_rows(text_renderer)

    def get_scroll_max(self):
        return ( max(0, len(self.rows) - (self.num_rows - 1)) )

    def compute_rows(self, text_renderer):
        all_rows = []

        all_words = self.text.split(" ")
        start_pos = 0

        temp_row = ""
        for word in all_words:

            if (word == "\n"):

                temp_row = temp_row + word
                all_rows.append([start_pos, temp_row])
                start_pos = start_pos + len(temp_row)

                temp_row = ""

            elif (text_renderer.size(temp_row) + text_renderer.size(word + " ") <= self.get_width() - (self.padding * 2)):
                temp_row = temp_row + word + " "

            else:
                # Append it to the list of rows and begin a new row
                all_rows.append([start_pos, temp_row])
                start_pos = start_pos + len(temp_row)

                # Start that new row with the word that was too long...
                temp_row = word + " "

        # Add the last, not-finished row to our list of rows
        all_rows.append([start_pos, temp_row])

        if (self.row_bounds[0] < 0):
            self.row_bounds[0] = 0

        # Clear the visible text list
        for each in self.text_visible:
            each = ""

        # Calculate the visible rows of text
        for a in range(self.row_bounds[0], len(all_rows)):
            if ( (a - self.row_bounds[0]) < self.num_rows):
                self.text_visible[ (a - self.row_bounds[0]) ] = all_rows[a][1]

        # Save the number of rows we need
        self.total_rows = len(all_rows)

        if (self.scroll_point + self.num_rows >= self.total_rows):
            self.scroll_point = self.total_rows - (self.num_rows - 1)

            if (self.scroll_point < 0):
                self.scroll_point = 0

        return all_rows

    def move_cursor(self, p_dx, text_renderer):
        if (p_dx == "end"):
            self.cursor_position = len(self.text)
        elif (p_dx == "home"):
            self.cursor_position = 0
            self.current_row = 0
            self.compute_rows(text_renderer)
        else:
            self.cursor_position += p_dx
            self.cursor_offset += p_dx

            if (self.cursor_position < 0):
                self.cursor_position = 0

            if (self.cursor_position > len(self.text)):
                self.cursor_position = len(self.text)

        for i in range(0, self.num_rows):
            if (self.bounds[i][1] > len(self.text)):
                self.bounds[i][1] = len(self.text)

        # Calculate for a one-line text box (horizontal scrolling)
        if (self.num_rows == 1):
            if (self.cursor_position > self.bounds[self.current_row][1]):
                self.bounds[self.current_row][1] = self.cursor_position

                i = self.bounds[0][1] - 1
                while (i >= 0):
                    if (text_renderer.size(sub_str(self.text, i, self.bounds[0][1])) <= self.get_width() - (self.padding * 2)):
                        self.bounds[0][0] = i
                    else:
                        break

                    i -= 1

                self.text_visible[0] = sub_str(self.text, self.bounds[0][0], self.bounds[0][1])

            if (self.cursor_position < self.bounds[self.current_row][0]):
                self.bounds[0][0] = self.cursor_position

            i = self.bounds[0][0] + 1

            while (i <= len(self.text)):
                if (text_renderer.size(sub_str(self.text, self.bounds[0][0], i)) <= self.get_width()):
                    self.bounds[0][1] = i
                else:
                    break

                i += 1

            self.text_visible[0] = sub_str(self.text, self.bounds[0][0], self.bounds[0][1])

        # Calculate for a multi-line textbox (vertical scrolling)
        else:

            if (self.cursor_position < 0):
                self.cursor_position = 0

            elif (self.cursor_position > len(self.text)):
                self.cursor_position = len(self.text)

            # If the cursor is earlier than the start of the row at the scroll point,
            # then move the scroll point to the row with the cursor on it
            if (len(self.rows) > 0):
                while (self.cursor_position < self.rows[self.scroll_point][0]):
                    self.scroll_to(self.scroll_point - 1)

                # Now, find out the cursor count of the last visible letter... if the cursor
                # has moved beyond that, we'll need to scroll down.
                row_to_check = self.scroll_point + (self.num_rows - 1)
                if (row_to_check >= len(self.rows)):
                    row_to_check = len(self.rows) - 1

                while (self.cursor_position > self.rows[row_to_check][0] + len(self.rows[row_to_check][1])):
                    self.scroll_to(self.scroll_point + 1)
                    row_to_check += 1
                    if (row_to_check >= len(self.rows)):
                        row_to_check = len(self.rows) - 1

            # Now let's find out which row the cursor is on to determine its x offset
            self.current_row = self.scroll_point # We'll assume first row and then check subsequent rows

            # Make sure there's a next row to check against...
            if (self.current_row + 1 < len(self.rows)):

                while (self.cursor_position > self.rows[self.current_row + 1][0]):
                    self.current_row += 1

                    # Again make sure there'll be a next row...
                    if (self.current_row + 1 >= len(self.rows)):
                        break

            # Ok, now that we know the row, we can find the x offset
            # What we'll do is take the substring from the character offset
            # at which the current line begins and the cursor position
            # and just check the rendered width of that substring.  :)
            if (len(self.rows) > 0):
                self.x_offset = 1 + self.get_x() + text_renderer.size(sub_str(self.rows[self.current_row][1], 0, self.cursor_position - self.rows[self.current_row][0]))
            else:
                self.x_offset = 1 + self.get_x()


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing this text box
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)


        # Check to see if we've decided to redact this text field.
        if (self.redacted):

            # Disable flag
            self.redacted = False

            # Set text to empty string
            self.set_text("", text_renderer)


        # Render position
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )


        # Align centered?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # Align right?
        if (self.align == "right"):

            rx -= self.get_width()


        self.active = 0

        if (self.getter):
            self.scroll_to(self.getter())

        # Get mouse location
        pos_mouse = pygame.mouse.get_pos()

        # Check to see if we've clicked on the text box to activate text entry
        if (mouse["clicked"]):

            # First set active to 0; if it turns out we clicked on the text box,
            # we'll set it to active after all.
            self.editing = 0

            # Go ahead and blur when clicked.  We will re-focus if the user re-clicked an active text box.
            self.blur()


            # If the mouse intersects with the text box and no other GUI element is atop it, then make it active
            result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (rx, ry, self.get_width(), self.get_render_height(text_renderer)) )

            if (result):

                # Mark as having mouse
                self.processed_mouse = True

                # Text boxes are a little weird.  Retain focus until a click occurs away from the input area.  Let's always focus when clicked...
                self.focus()


                self.editing = 1

                # Now let's figure out where they clicked.  We begin by checking for row of clicking
                row_clicked = self.scroll_point + (pos_mouse[1] - (ry)) / self.get_render_height(text_renderer) # self.height designates the height of one row

                # Make sure that row exists
                if (row_clicked >= len(self.rows)):
                    row_clicked = len(self.rows) - 1

                # We have the row; now let's use the mouseX offset data to find out which character
                # they clicked around...
                mouse_x_offset = pos_mouse[0] - rx

                aggregate_width = 0
                placed_cursor = False

                if (len(self.rows) > 0):
                    for i in range(0, len(self.rows[row_clicked][1])):
                        aggregate_width += text_renderer.size("%s" % self.rows[row_clicked][1][i])

                        if (aggregate_width > mouse_x_offset):
                            new_cursor_position = self.rows[row_clicked][0] + i
                            self.cursor_offset = i

                            self.move_cursor(new_cursor_position - self.cursor_position, text_renderer)

                            placed_cursor = True
                            break

                    # They probably clicked on a line that the text doesn't fully span
                    # so we'll put the cursor at the end of that line.
                    if (not placed_cursor):
                        new_cursor_position = self.rows[row_clicked][0] + len(self.rows[row_clicked][1])
                        self.cursor_offset = len(self.rows[row_clicked][1])

                        self.move_cursor(new_cursor_position - self.cursor_position, text_renderer)

                else:
                    self.move_cursor("end", text_renderer)

            else:

                # Flag as not having mouse
                self.processed_mouse = False

                # If we had the mouse last time, then blur
                if (self.processed_mouse_last_time):

                    # Blur
                    self.blur()

        # Check for mouse scrolling
        if (mouse["scrolled"] == "down"):
            self.scroll_to(self.scroll_point + 1)

        elif (mouse["scrolled"] == "up"):
            self.scroll_to(self.scroll_point - 1)

        # Check for text input if active
        if (self.editing == 1):

            # Now, read whatever text is in the keyboard queue and insert it into the string
            keyboard_buffer = system_input["key-buffer"]

            if (len(keyboard_buffer) > 0):
                log( "buffer:  ", keyboard_buffer )
                self.text = insert_char(keyboard_buffer, self.text, self.cursor_position)
                self.rows = self.compute_rows(text_renderer)
                self.move_cursor(len(keyboard_buffer), text_renderer)

                # Raise on-change events
                results.append(
                    self.raise_action("change")
                )

            # See if the user pressed the backspace key
            if (self.backspace_wait > 0):
                self.backspace_wait -= 1

            if (pygame.key.get_pressed()[K_BACKSPACE] and self.backspace_wait <= 1):

                # If the user is holding down backspace to eliminate many characters
                # in succession, we'll be at the very end of the countdown (at == 1)...
                # since they want to erase quickly, we'll use a lower delay in this case
                if (self.backspace_wait == 1):
                    self.backspace_wait = 5
                else:
                    self.backspace_wait = 50

                if (len(self.text) > 0):

                    # Get the portion of the string leading up to the letter before the cursor
                    temp_str = sub_str(self.text, 0, self.cursor_position - 1)

                    # If the cursor isn't at the very end of the text, then grab what's after the cursor as well
                    if (self.cursor_position < len(self.text)):
                        temp_str = temp_str + sub_str(self.text, self.cursor_position, len(self.text))

                    # Set the text to "temp_str" which features the edited text
                    self.text = temp_str

                    # Recalculate all of the rows
                    self.rows = self.compute_rows(text_renderer)

                    # Move the cursor back one space
                    self.move_cursor(-1, text_renderer)


                    # Raise on-change events
                    results.append(
                        self.raise_action("change")
                    )

            # Reset backspace wait if necessary
            if (not pygame.key.get_pressed()[K_BACKSPACE]):
                self.backspace_wait = 0

            # Decrease return_wait
            if (self.return_wait > 0):
                self.return_wait -= 1

            # See if the user pressed RETURN
            #if (pygame.key.get_pressed()[K_RETURN] and self.return_wait <= 1):
            #    self.text = insert_char(" \n ", self.text, self.cursor_position)
            #    self.move_cursor(1, text_renderer)

            #    if (self.return_wait == 1):
            #        self.return_wait = 5
            #    else:
            #        self.return_wait = 50

            # Reset the return_wait counter if the user lifts the key
            #if (not pygame.key.get_pressed()[K_RETURN]):
            #    self.return_wait = 0

            if (self.left_arrow_wait > 0):
                self.left_arrow_wait -= 1

            # Handle potential cursor movement...
            if (pygame.key.get_pressed()[K_LEFT] and self.left_arrow_wait <= 1):
                # Same idea as with backspace...
                if (self.left_arrow_wait == 1):
                    self.left_arrow_wait = 5
                else:
                    self.left_arrow_wait = 50

                # As long as we're not at the beginning already, move left...
                if (self.cursor_position > 0):
                    self.move_cursor(-1, text_renderer)

                    # If we're holding control, then move to the previous word
                    if (pygame.key.get_pressed()[K_LCTRL]):

                        i = self.cursor_position - 1
                        while (i > 0):
                            if (self.text[i] == " "):
                                self.move_cursor(i - (self.cursor_position - 1), text_renderer)
                                break

                            i -= 1

                            if (i == 0):
                                self.move_cursor("home", text_renderer)

            # Reset move-left wait if necessary
            if (not pygame.key.get_pressed()[K_LEFT]):
                self.left_arrow_wait = 0

            ###

            if (self.right_arrow_wait > 0):
                self.right_arrow_wait -= 1

            if (pygame.key.get_pressed()[K_RIGHT] and self.right_arrow_wait <= 1):
                # Same idea again...
                if (self.right_arrow_wait == 1):
                    self.right_arrow_wait = 5
                else:
                    self.right_arrow_wait = 50

                if (self.cursor_position < len(self.text)):
                    self.move_cursor(1, text_renderer)

                    if (pygame.key.get_pressed()[K_LCTRL]):

                        i = self.cursor_position
                        while (i < len(self.text)):
                            if (self.text[i] == " "):
                                self.move_cursor(i - (self.cursor_position - 1), text_renderer)
                                break

                            i += 1

                            if (i == len(self.text)):
                                self.move_cursor("end", text_renderer)

            if (not pygame.key.get_pressed()[K_RIGHT]):
                self.right_arrow_wait = 0

            ###

            if (pygame.key.get_pressed()[K_HOME]):
                self.move_cursor("home", text_renderer)

            if (pygame.key.get_pressed()[K_END]):
                self.move_cursor("end", text_renderer)


            # HIt TAB to advance to the next input field
            if ( K_TAB in control_center.get_input_controller().get_system_input()["keydown-keycodes"] ):

                # If holding shift, go to the previous...
                if ( pygame.key.get_pressed()[K_LSHIFT] or pygame.key.get_pressed()[K_RSHIFT] ):

                    # Raise a "go to previous input" event
                    results.add(
                        action = "previous:input",
                        params = {
                            "caller": self.name
                        }
                    )

                else:

                    # Raise a "go to next input" event
                    results.add(
                        action = "next:input",
                        params = {
                            "caller": self.name
                        }
                    )


            # Hit ENTER to "submit" the text field (presumably raising the same event as an "ok" button might do)
            elif ( K_RETURN in control_center.get_input_controller().get_system_input()["keydown-keycodes"] ):

                # Raise submit events
                results.append(
                    self.raise_action("submit")
                )


        # Is the mouse over this element?
        r = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (rx, ry, self.get_width(), self.get_height(text_renderer)) )
        if (r and (not masked)):
            self.active = 1

            #return True # If so, then tell the GUI Handler not to allow the mouse to touch lower elements
        #return False # If not, the mouse has the freedom to touch lower elements

        # Return resultant events
        return results


    # Render text box
    def draw(self, sx, sy, text_renderer, window_controller):

        self.blink_wait += 1

        if (self.blink_wait >= self.blink_wait_delay):
            self.blink_wait = 0

            self.blinking = (not self.blinking)


        """
        if (self.editing):
            self.current_background = self.background_active
            self.current_border_color = self.border_color_active

        else:
            self.current_background = self.background
            self.current_border_color = self.border_color
        """

        # Render position
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )


        # Align centered?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # Align right?
        if (self.align == "right"):

            rx -= self.get_width()


        # frame it
        #draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height(), self.border_color, 1)

        #self.render_background(text_renderer, sx, sy)
        Widget.__std_render_border__( self, rx, ry, self.get_width(), self.get_render_height(text_renderer), window_controller, rounded = self.get_has_rounded_corners() )

        # Handle drawing for single-line box
        if (self.num_rows == 1):
            text_renderer.render_with_wrap(self.text_visible[0], rx + self.get_padding_left(), ry + self.get_padding_top(), self.get_color())

        # Handle drawing for multi-line box
        else:
            for i in range(self.scroll_point, self.scroll_point + self.num_rows):
                if (i < len(self.rows)):
                    if (self.center):
                        text_renderer.render_with_wrap(self.rows[i][1], sx + self.get_x() + (available_width / 2), sy + self.get_y() + ( (i - self.scroll_point) * self.height), self.text_color, align = "center")
                    else:
                        text_renderer.render_with_wrap(self.rows[i][1], sx + self.get_x() + self.padding, sy + self.get_y() + ( (i - self.scroll_point) * self.height), self.text_color)

        # Highlight the frame on mouseover to say "hey!  click me if you want to edit me!"
        #if (self.active):
        #    draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height(), (255, 0, 0), 1)

        # If it's active, then display a cursor
        if (self.editing == 1):

            # First, I want to draw a cursor so we know where we are editing at
            if (self.num_rows == 1):
                self.x_offset = rx + self.get_padding_left() + text_renderer.size(self.text[self.bounds[0][0] : self.cursor_position])

                if (self.blinking):
                    draw_rect(self.x_offset, ry + self.get_padding_top(), 1, text_renderer.font_height, (37, 135, 255))

            else:

                try:
                    self.x_offset = sx + self.get_x() + self.padding + text_renderer.size(self.text[self.bounds[self.current_row][1] : self.cursor_position])
                except:
                    pass

                try:
                    self.x_offset = sx + self.get_x() + self.padding + text_renderer.size(self.text_visible[self.current_row - self.scroll_point][0 : self.cursor_offset])
                except:
                    self.x_offset = self.padding
                #print self.text[self.bounds[self.current_row][1] : self.cursor_position]

                if (self.x_offset >= 0):
                    if (self.current_row >= self.scroll_point and self.current_row < (self.scroll_point + self.num_rows)):

                        if (self.blinking):
                            draw_rect(self.x_offset, sy + self.get_y() + (self.current_row - self.scroll_point) * self.height, 1, self.height, (37, 135, 255))

        #text_renderer.render_with_wrap( self.get_bloodline(), 5, sy + self.get_y(), (225, 225, 25) )


class Rectangle(Element):

    def __init__(self, x, y, width, height):

        Element.__init__(self, "rect", x, y, width, height)


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        pos_mouse = pygame.mouse.get_pos()

        return results


        r = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.height) )
        #if (r):
        #    return True
        #return False

        # No evnets to return
        return EventQueue()


    # Render rectangle
    def draw(self, sx, sy, text_renderer, window_controller):

        # Get alpha interval
        alpha = self.get_background_alpha() * self.alpha_controller.get_interval()

        #print sx, sy, self.height, self.get_x(), self.get_y()

        draw_rect(
            self.get_x() + sx,
            self.get_y() + sy,
            self.get_width(),
            self.height,
            set_alpha_for_rgb( alpha, self.get_gradient_start() )
        )

        #text_renderer.render_with_wrap( "%d, %d" % (self.get_x() + sx, self.get_y() + sy), self.get_x() + sx, self.get_y() + sy, (225, 225, 25) )
        return

        # Draw rect
        draw_rect_with_horizontal_gradient(
            self.get_x() + sx,
            self.get_y() + sy,
            self.get_width(),
            self.height,
            set_alpha_for_rgb( alpha, self.get_gradient_start() ),
            set_alpha_for_rgb( alpha, self.get_gradient_end() )
        )

        #if (self.framed):
        #    draw_rect_frame(self.get_x() + sx, self.get_y() + sy, self.get_width(), self.height, self.frame_color, 2)


class Hidden(Element):

    def __init__(self, value = None):

        Element.__init__(self, "hidden", 0, 0)

        # Track the value of this hidden widget
        self.value = value


    # Set value
    def set_value(self, value):

        self.value = value


    # Get value
    def get_value(self):

        return self.value


    # No processing
    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Hidden element would never return an event
        return EventQueue()


    # Draw... or don't draw, anyway...
    def draw(self, sx, sy, text_renderer, window_controller):

        # Nothing to render
        return


class Listener(Element):

    def __init__(self, p_source, p_callback):

        Element.__init__(self, (0, 0))

        self.element_type = "Listener"

        self.source = p_source
        self.callback = p_callback

    def get_rect(self):
        return (0, 0, 0, 0)

    def draw(self, sx, sy, text_renderer, window_controller):
        return

    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):
        if (self.source and self.callback):
            self.callback(self.source())

        return False

class Label(Element):

    def __init__(self, text, x, y, align = "left", max_width = 1000):#p_coords, styles=[], background=None, text_color=(0, 0, 0), text_color_active=(0, 0, 0), style="", align = None):

        Element.__init__(self, "label2", x, y)

        # Label text
        self.text = text

        # We can optionally specify a specific font to render with
        self.font_family = None

        # We'll eventually track label width (?)
        self.current_width = 0

        # Text alignment
        self.align = align

        # Max width (for text wrapping)
        self.max_width = max_width


    # Configure
    def configure(self, options):

        # Standard Element configure
        Element.configure(self, options)


        if ( "font-family" in options ):
            self.font_family = options["font-family"]


        # For chaining
        return self


    # Change max widget
    def set_max_width(self, max_width):

        self.max_width = max_width


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

            # Word wrap
            lines = text_renderer.wordwrap_text( self.text, 0, 0, (225, 225, 225), max_width = self.get_width() )

            # Content?
            if ( len(lines) > 0 ):

                metric = max( o["width-used"] for o in lines )

            # Cache
            self.cache_metric("render-width", metric)

            # Return
            return metric


    # Get widget height
    def report_widget_height(self, text_renderer):

        # Try to get cached version
        metric = self.get_cached_metric("render-height")

        # Validate
        if (metric != None):

            # Return
            return metric

        # Compute, then cache...
        else:

            # Compute
            metric = 0

            # Word wrap
            lines = text_renderer.wordwrap_text( self.text, 0, 0, (225, 225, 225), max_width = self.get_width() )

            # Calculate height needed
            metric = ( len(lines) * text_renderer.font_height )

            # Cache
            self.cache_metric("render-height", metric)

            # Return
            return metric


    # Set label text
    def set_text(self, text, text_renderer):

        # Update text
        self.text = text

        # Recalculate width used
        self.current_width = text_renderer.size(self.text)


    # Get active label text
    def get_text(self):

        return self.text


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Standard element processing
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        (mx, my) = pygame.mouse.get_pos()

        r = (sx + self.get_x(), sy + self.get_y(), self.report_widget_width(text_renderer), 25)
        mr = (mx, my, 1, 1)

        self.active = False

        if ( (not masked) and ( intersect(r, mr) ) ):

            # Flag as having mouse
            self.processed_mouse = True

            # If we didn't have the mouse last time, then we should change this widget's css state to "active"
            if (not self.processed_mouse_last_time):

                # Focus widget
                self.focus()

                #print self.get_bloodline()
                #print 5/0


            if ( mouse["clicked"] ):

                # Fire click events
                results.append(
                    self.raise_action("click")
                )

        else:

            # Flag as not having mouse
            self.processed_mouse = False

            # If we previously processed the mouse, then we should remove the "active" state from this widget
            if (self.processed_mouse_last_time):

                # Blur widget
                self.blur()

        # Return resultant events
        return results
        pos_mouse = pygame.mouse.get_pos()

        r = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (self.get_x(), self.get_y(), text_renderer.size(self.text), self.height) )
        if (r):
            return True

        return False


    # Render label
    def draw(self, sx, sy, text_renderer, window_controller):

        # Check for custom font
        if (self.font_family):

            text_renderer = window_controller.get_text_controller_by_name(self.font_family).get_text_renderer()

        background = None
        if (background != None):
            draw_rect(self.get_x() + sx, self.get_y() + sy, text_renderer.size(self.text), 32, background)

        border_color = None
        if (border_color != None):
            draw_rect_frame(self.get_x() + sx, self.get_y() + sy, text_renderer.size(self.text), 32, border_color, border_size)

        (x, y) = (
            sx + self.get_x(),
            sy + self.get_y()
        )

        if (self.align == "center"):
            x -= int( self.report_widget_width(text_renderer) / 2 )

        elif (self.align == "right"):
            x -= self.report_widget_width(text_renderer)

        Widget.__std_render_border__( self, x, y, self.report_widget_width(text_renderer) + self.get_padding_left() + self.get_padding_right(), self.get_render_height(text_renderer), window_controller, rounded = self.get_has_rounded_corners() )

        # Track last known render position
        self.last_render_x = x
        self.last_render_y = y

        x += self.get_padding_left()
        y += self.get_padding_top()

        text_renderer.render_with_wrap(self.text, x, y, self.get_color(), 1000 + self.max_width, align = "left")


class Dialog(Element):

    def __init__(self, x, y, width, height, root = False):#p_x, p_y, p_width, p_height, background = None, background_active = None, border_color = None, process_function=None, has_rounded_corners = True, is_floating = False):

        Element.__init__(self, "dialog", x, y, width, height)

        # Give the dialog its own in-house GUI manager
        self.gui_manager = GUI_Manager()

        # Track whether this is a root dialog, or a dialog within another widget/dialog...
        self.root = root

        # Widgets that we add to this dialog
        self.widgets = []

        # (?)
        self.actions = {}

        # Dialog can be modal
        self.modal = False

        #self.process_function = process_function
        #self.process_callback = None

        #self.is_floating = is_floating


    # Overwrite
    def configure_alpha_controller(self, options):

        # Standard configuration
        Widget.configure_alpha_controller(self, options)

        # Forward to children
        for widget in self.widgets:

            # Cascade
            widget.configure_alpha_controller(options)

    # Configure
    def configure(self, options):

        # Standard element configure
        Element.configure(self, options)


        if ( "modal" in options ):
            self.modal = ( int( options["modal"] ) == 1 )


        # For chaining
        return self


    # A dialog's "widget" height is equal to the height required to render each widget within the dialog
    def report_widget_height(self, text_renderer):

        return max( ( widget.get_y() + widget.get_box_height(text_renderer) ) for widget in self.widgets )


    """
    # Overwrite
    def show(self):

        self.visible = True

        if (self.child):

            self.child.show()

        for widget in self.widgets:

            widget.show()

        #for name in self.gui_manager.widgets:
        #    self.gui_manager.widgets[name].show()
    """


    """
    # Overwrite
    def hide(self):

        self.visible = False

        if (self.child):

            self.child.hide()

        for widget in self.widgets:

            widget.hide()
        #for name in self.gui_manager.widgets:
        #    self.gui_manager.widgets[name].hide()
    """


    # Forward updated css state to list elements on focus
    def on_focus(self):

        # Loop widgets
        for widget in self.widgets:

            # Update bloodline for children
            widget.css({
                "bloodline": self.get_bloodline()
            })

            widget.on_focus()

            #widget.focus()


    # Forward updated css state to list elements on blur
    def on_blur(self):

        # Loop widgets
        for widget in self.widgets:

            # Update each child's bloodline
            widget.css({
                "bloodline": self.get_bloodline()
            })

            widget.on_blur()

            #widget.blur()


    def on_show(self, target, animated, on_complete):

        for widget in self.widgets:

            widget.show(target, animated, on_complete)

    def on_hide(self, target, animated, on_complete):

        for widget in self.widgets:

            widget.hide(target, animated, on_complete)


    def has_mouse(self, offset):
        self_has_mouse = self.is_visible() and intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (self.get_x(), self.get_y(), self.get_width(), self.get_height()) )
        child_has_mouse = False

        if (self.child):
            child_has_mouse = self.child.is_visible() and self.child.has_mouse(offset)

        for widget in self.widgets:

            if ( widget.has_mouse(offset) ):

                child_has_mouse = True
        #for (type, each) in self.elements:
        #    if (each.has_mouse(offset)):
        #        child_has_mouse = True

        return (self_has_mouse or child_has_mouse)


    # Overwrite - we always consider a dialog to have performed mouse processing if it's modal
    def performed_mouse_processing(self):

        # Check flag
        return (self.modal) or (self.processed_mouse)


    # Add a widget to the dialog
    def add_widget(self, widget):

        # New widget
        self.widgets.append(
            widget.css({
                "bloodline": self.get_bloodline()
            }).configure({
                "max-width": self.get_width()
            })
        )

        #self.widgets[-1].blur()


    # Something of a hacky redirect
    def get_widget_by_name(self, name):

        # Loop widgets
        for widget in self.widgets:

            # check widget name
            if ( widget.get_name() == name ):

                return widget

        # Couldn't find it
        return None
        # Need to peek into the in-house GUI manager
        return self.gui_manager.get_widget_by_name(name)


    # Get all direct-descendant widgets of a given type
    def get_widgets_by_selector(self, selector):

        # Matches
        results = []

        # Loop widgets
        for widget in self.widgets:

            # Match?
            if ( widget.selector == selector ):

                # Append
                results.append(widget)

        # Results
        return results


    # find a widget by a given name within this dialog
    def find_widget_by_name(self, name):

        # Loop widgets
        for widget in self.widgets:

            # Check this widget
            if ( widget.get_name() == name ):

                # Matched
                return widget

            # Search children, if possible
            else:

                # Let's see if we can find it nested
                nested_widget = widget.find_widget_by_name(name)

                # Result?
                if (nested_widget):

                    # We found the widget
                    return nested_widget

                #else:
                #    print "no match in '%s'" % widget.get_name()


        # Check the child as a last resort
        if (self.child):

            # Try to find it in the child
            nested_widget = self.child.find_widget_by_name(name)

            # Match?
            if (nested_widget):

                # Found it, finally!
                return nested_widget


        # We couldn't find it...
        return None


    # Find all widgets of a given selector type
    def find_widgets_by_selector(self, selector):

        # Track matches
        matches = []

        # Loop widgets
        for widget in self.widgets:

            # Compare selector
            if ( widget.selector == selector ):

                # Match
                matches.append(widget)

            # Check for children, also...
            matches.extend(
                widget.find_widgets_by_selector(selector)
            )


        # Return matches
        return matches


    """
    def get_element(self, p_id):
        for (id, e) in self.elements:
            if (id == p_id):
                return e

        return None
    """


    # Get all elements of a given selector type
    def get_elements_by_selector(self, selector):

        # Track matches
        results = []

        # Loop widgets
        for widget in self.widgets:

            # Match?
            if (widget.selector == selector):

                # Add to results
                results.append(widget)

        # Return matches
        return results


    def get_elements_with_aliases_by_type(self, element_type):

        results = []

        for (alias, e) in self.elements:

            if (e.element_type == element_type or element_type == "*"):
                results.append( (alias, e) )

        return results

    def define_action(self, p_id, p_action):
        self.actions[p_id] = p_action


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        #if (not masked):
        #    if (intersect( (self.get_x() + sx, self.get_y() + sy, self.get_width(), self.get_height(text_renderer)), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):
        #        if (pygame.mouse.get_pressed()[1]):
        #           self.coords = (pygame.mouse.get_pos()[0] - 24, pygame.mouse.get_pos()[1] - 24)

        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)


        # Raise onload events if necessary
        if (not self.loaded):

            # Flag as loaded
            self.loaded = True

            # Raise onload events
            results.append(
                self.raise_action("load")
            )


        # Default offset
        # Rendering position
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )


        # X align center?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx -= self.get_width()


        # Y align center?
        if (self.valign == "center"):

            ry -= int( self.report_widget_height(text_renderer) / 2 )

        # Y align bottom?
        elif (self.valign == "bottom"):

            ry -= self.report_widget_height(text_renderer)


        # Update mouse processing flag for overall dialog
        self.processed_mouse = ( not masked ) and ( intersect( (rx, ry, self.get_width(), self.get_render_height(text_renderer)), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), quick = True ) )

        # Factor in padding as we prepare to render child widgets
        rx += self.get_padding_left()
        ry += self.get_padding_top()


        for widget in self.widgets:

            # Only process visible / becoming visible widgets
            if ( (widget.alpha_controller.get_interval() > 0) or (widget.alpha_controller.get_target() > 0) ):

                results.append(
                    widget.process(rx, ry, text_renderer, control_center, masked = masked, system_input = system_input, mouse = mouse)
                )

                # Update masked flag; did this widget process the mouse?
                masked |= widget.performed_mouse_processing()

                # If the widget exceeds the reported size of the dialog (e.g. dropdowns), we'll still count the dialog as having the mouse if the mouse intersects the overflow
                self.processed_mouse |= widget.performed_mouse_processing()


        # Does this dialog have a child to process?
        if (self.child):

            if ( (self.processed_mouse) or (self.child.alpha_controller.get_target() > 0) ):

                self.child.show()
                #print self.processed_mouse, self.child.alpha_controller.get_interval()

                # Determine ideal child rendering point.
                # Assume to the right...
                (rx, ry) = (
                    sx + self.get_x() + self.get_width(),
                    sy + self.get_y()
                )

                # If that rendering point would put the child offscreen, let's move it to the left...
                if ( (rx + self.child.get_width()) > SCREEN_WIDTH ):

                    # Flip
                    rx = ( ( sx + self.get_x() ) - self.child.get_width() )


                # Process the child widget
                results.append(
                    self.child.process(rx, ry, text_renderer, control_center, masked = masked, system_input = system_input, mouse = mouse)
                )

                # Track masked flag
                masked |= self.child.performed_mouse_processing()

                # If the child widget performed mouse processing, then this parent dialog did as well, even though the child is "out of bounds" in relation to the dialog's rendering area.
                self.processed_mouse |= self.child.performed_mouse_processing()


                # If neither the dialog nor its child processed the mouse, then hide the child
                if (not self.processed_mouse):

                    # Hide child
                    self.child.alpha_controller.configure({
                        "interval": 0,
                        "target": 0
                    })

                #print self.child, self.child.alpha_controller.get_interval()


        # Root dialogs will check for tab cycle events
        if (self.root):

            # Peek into the results (without removing them) and see if we can find a tab cycle event
            for event in results._get_queue():

                # Convenience
                (action, params) = (
                    event.get_action(),
                    event.get_params()
                )

                if ( action == "next:input" ):

                    # Get all of the input widgets within this dialog
                    inputs = self.find_widgets_by_selector("input")

                    # Find the input that called for the cycle
                    caller = self.find_widget_by_name( params["caller"] )

                    # Validate caller
                    if (caller):

                        # Loop
                        for i in range( 0, len(inputs) ):

                            # Is this the one that made the call?
                            if ( inputs[i] == caller ):

                                # Get the index of the next input
                                next_index = i + 1

                                # Bounds check
                                if ( next_index >= len(inputs) ):

                                    # Wrap
                                    next_index = 0


                                # Deactivate calling input
                                caller.deactivate()

                                # Activate next widget
                                inputs[next_index].activate()

                elif ( action == "previous:input" ):

                    # Get all of the input widgets within this dialog
                    inputs = self.find_widgets_by_selector("input")

                    # Find the input that called for the cycle
                    caller = self.find_widget_by_name( params["caller"] )

                    # Validate caller
                    if (caller):

                        # Loop
                        for i in range( 0, len(inputs) ):

                            # Is this the one that made the call?
                            if ( inputs[i] == caller ):

                                # Get the index of the previous input
                                previous_index = i - 1

                                # Bounds check
                                if ( previous_index < 0 ):

                                    # Wrap
                                    next_index = ( len(inputs) - 1 )


                                # Deactivate calling input
                                caller.deactivate()

                                # Activate next widget
                                inputs[previous_index].activate()


            # Also, root-level dialogs can check for escape events
            if ( K_ESCAPE in control_center.get_input_controller().get_system_input()["keydown-keycodes"] ):

                # Raise submit events
                results.append(
                    self.raise_action("escape")
                )


        if (self.processed_mouse):

            # If not last time, focus and raise mouseover action
            if (not self.processed_mouse_last_time):

                # Focus
                self.focus()

                # Raise mouseover action
                results.append(
                    self.raise_action("mouseover")
                )

        else:

            # If we had the mouse last time, blur and raise mouseout action
            if (self.processed_mouse_last_time):

                # Blur
                self.blur()

                # Raise mouseout action
                results.append(
                    self.raise_action("mouseout")
                )
                #print "MOUSEOUT for %s" % self.name

        return results

        return results
        if (masked or intersect( (self.get_x() + sx, self.get_y() + sy, self.get_width(), self.get_height(text_renderer)), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):
            return True

        #elif (self.is_floating):
        #    self.hide()

        return False


    # Render dialog and child widgets
    def draw(self, sx, sy, text_renderer, window_controller):

        # Render lightbox?
        if (self.uses_lightbox):

            # Blanket screen
            draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, self.alpha_controller.get_interval() / 2))

        # Rendering position
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y() + self.get_margin_top()
        )


        # X align center?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx -= self.get_width()


        # Y align center?
        if (self.valign == "center"):

            ry -= int( self.report_widget_height(text_renderer) / 2 )

        # Y align bottom?
        elif (self.valign == "bottom"):

            ry -= self.report_widget_height(text_renderer)


        if (self.report_widget_height(text_renderer) > 0):

            Widget.__std_render_border__( self, rx, ry, self.get_width(), self.get_render_height(text_renderer), window_controller, rounded = self.get_has_rounded_corners() )
            #self.render_background(text_renderer, sx, sy)

        rx += self.get_padding_left()
        ry += self.get_padding_top()

        # Loop widgets
        for widget in self.widgets:

            # Only render the widget if it's visible (or set to become visible)
            if ( (widget.alpha_controller.get_interval() > 0) or (widget.alpha_controller.get_target() > 0) ):

                # Render widget
                widget.draw(rx, ry, text_renderer, window_controller)

            #draw_rect( sx + self.get_x() + widget.x, sy + self.get_y() + widget.y, widget.width, widget.report_widget_height(text_renderer), (225, 225, 25, 0.15) )


        # If this dialog has a child, render an arrow -->
        if (self.child):

            # Arrow size, padding
            arrow_size = 8
            arrow_padding = 4

            # Arrow rendering position
            (rxArrow, ryArrow) = (
                sx + self.get_x() + self.get_width() - arrow_size - arrow_padding,
                sy + self.get_y() + int( self.get_render_height(text_renderer) / 2 ) - int( arrow_size / 2 )
            )

            # Render arrow
            draw_triangle(rxArrow, ryArrow, arrow_size, arrow_size, self.get_color(), None, DIR_RIGHT)


        """
        if (self.css_class == "format"):
            text_renderer.render_with_wrap( "%s (%d / %d)" % (self.get_bloodline(), len(self.widgets), self.get_render_height(text_renderer)), 0, ry, (225, 225, 25))
        elif (self.css_class in ("modal", "title-bar")):
            text_renderer.render_with_wrap( "%s, %s" % (self.get_gradient_start(), self.get_gradient_end()), 640, ry, (225, 225, 25), align = "right")
        """


        #draw_rect_frame( sx + self.get_x(), sy + self.get_y(), self.get_width(), self.report_widget_height(text_renderer), (225, 25, 25, 0.5), 2 )

        #draw_rect(rx, ry, self.get_width(), self.report_widget_height(text_renderer), (225, 25, 25, 0.35))
        #draw_rect(rx, ry, 100, self.get_render_height(text_renderer), (25, 25, 225, 0.35))

    # Dialog forwards this call to its widgets
    def render_overlays(self, sx, sy, text_renderer, window_controller):

        # Rendering position
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y() + self.get_margin_top()
        )


        # X align center?
        if (self.align == "center"):

            rx -= int( self.get_width() / 2 )

        # X align right?
        elif (self.align == "right"):

            rx -= self.get_width()


        # Y align center?
        if (self.valign == "center"):

            ry -= int( self.report_widget_height(text_renderer) / 2 )

        # Y align bottom?
        elif (self.valign == "bottom"):

            ry -= self.report_widget_height(text_renderer)


        rx += self.get_padding_left()
        ry += self.get_padding_top()

        for widget in self.widgets:

            widget.render_overlays(
                rx,
                ry,
                text_renderer,
                window_controller
            )


        # Does this dialog have a child to render?
        if (self.processed_mouse and self.child):

            # Determin ideal child rendering point.
            # Assume to the right...
            (rx, ry) = (
                sx + self.get_x() + self.get_width(),
                sy + self.get_y()
            )

            # If that rendering point would put the child offscreen, let's move it to the left...
            if ( (rx + self.child.get_width()) > SCREEN_WIDTH ):

                # Flip
                rx = ( ( sx + self.get_x() ) - self.child.get_width() )


            # Render child widget
            self.child.draw(rx, ry, text_renderer, window_controller)



class Tooltip(Element):

    def __init__(self, text, x, y, width, minimum_height, text_align = "left"):#text="", x=0, y=0, background=(50, 50, 50, 1.0), border_color=(255, 255, 255), text_color=(255, 255, 255), speed=0.02, hover=0, width="auto", minimum_height="auto", center_text=False, has_rounded_corners = False):

        Element.__init__(self, "tooltip", x, y, width = 0, height = 0)#(x, y), has_rounded_corners = True)
        #Fader.__init__(self, speed = speed, hover = hover)

        self.element_type = "Tooltip"

        # Tooltip text
        self.text = text

        # Text alignment
        self.text_align = text_align

        # Optionally specify a minimum height (?)
        self.minimum_height = minimum_height

        # Some tooltips appear letter-by-letter; these variables track cursor position.
        self.cursor = 0
        self.cursor_wait = 0

        self.limit = False

        self.line_count = 0


    def format(self, background=None, border_color=None, text_color=None):

        if (background):
            self.background = background

        if (border_color):
            self.border_color = border_color

        if (text_color):
            self.text_color = text_color

    def set_text(self, text, text_renderer = None):

        self.line_count = 1

        self.text = text.replace("<br>", "\n")
        self.text = text.replace("[br]", "\n")

        # If we don't automatically set the width of this tooltip,
        # then we'll need to split long lines automatically so that
        # they will fit into the specified with.
        if (self.get_width() != "auto" and self.text.replace(" ", "") != ""):

            # Split the text into the currently set lines...
            lines = self.text.split("\n")

            self.line_count = len(lines)

            # Loop through each line...
            i = 0
            while (i < len(lines)):

                # Keep track of the text of the current line and its width...
                current_line = ""
                current_line_width = 0

                # We're going to loop through each word, wrapping on a word-by-word basis...
                words = lines[i].split(" ")

                j = 0
                while (j < len(words)):

                    # Get the length of this word plus its trailing space
                    this_word_width = text_renderer.size(words[j] + " ")

                    # If we can still fit the word in, then add it as normal
                    if (current_line_width + this_word_width < (self.get_width() - 10) ):

                        # Add the word
                        current_line += words[j] + " "
                        # Keep track of the width we've used
                        current_line_width += this_word_width

                    # If we can't fit the word, then we're going to have to
                    # end the line at this point and move the rest to a new
                    # line.  (We'll then be checking that next line and so on.)
                    else:

                        # Set the current line to what fits.
                        lines[i] = current_line

                        # Reset the current line data and width tracking.
                        current_line = ""
                        current_line_width = 0

                        # We're going to grab all of the remaining words in this line
                        # and place them into a new line...
                        rest_of_line = ""

                        # Loop through remaining words...
                        for k in range(j, len(words)):
                            rest_of_line += "%s " % words[k]

                        # Now create a new line for the words that we couldn't fit.
                        lines.insert(i + 1, rest_of_line)

                        # Set j such that the while loop will not continue.
                        j = len(words)

                        self.line_count += 1

                    j += 1

                i += 1

            # Now, let's reset the text and then recreate it from the lines we calculated.
            self.text = ""

            for i in range(0, len(lines)):
                self.text += lines[i]

                if (i < len(lines) - 1):
                    self.text += "\n"

    def reset_cursor(self):

        self.cursor = 0
        self.cursor_wait = 0

    def shown_all(self):
        if (self.cursor >= len(self.text)):
            return True

        else:
            return False

    def get_text(self):
        return self.text

    def set_position(self, x=0, y=0):
        self.x = x
        self.y = y

    def get_width(self, text_renderer=None):
        if (not text_renderer):
            if (self.get_width() == "auto"):
                return 0
            else:
                return self.get_width()

        lines = self.text.split("\n")

        width = 0
        for line in lines:
            w = text_renderer.size(line)
            if (w > width):
                width = w

        width += 10

        return width

    def get_height(self):
        lines = self.text.split("\n")
        height = (len(lines) * 20) + 10

        if (self.minimum_height == "auto"):
            return height
        else:
            return max(self.minimum_height, height)

    def get_visible_height(self):
        return self.get_height()

    def draw(self, sx, sy, text_renderer, window_controller):
        #if (self.background):
        #    self.background = (self.background[0], self.background[1], self.background[2], self.gamma_value)
        #if (self.border_color):
        #    self.border_color = (self.border_color[0], self.border_color[1], self.border_color[2], self.gamma_value)
        #if (self.text_color):
        #    self.text_color = (self.text_color[0], self.text_color[1], self.text_color[2], self.gamma_value)
        self.current_background = self.background
        self.current_border_color = self.border_color

        self.render_background(text_renderer, sx, sy)

        lines = self.text.split("\n")

        width = 0

        if (self.width == "auto"):
            for line in lines:
                w = text_renderer.size(line)
                if (w > width):
                    width = w

            width += 10

        else:
            width = self.get_width()

        height = (len(lines) * 20) + 10
        if (self.minimum_height != "auto"):
            height = max(self.minimum_height, height)

        #if (self.background):
        #    draw_rect(self.get_x() + sx, self.get_y() + sy, width, height, self.background)
        #if (self.border_color):
        #    draw_rect_frame(self.get_x() + sx, self.get_y() + sy, width, height, self.border_color, 1)

        if (not self.limit):
            for i in range(0, len(lines)):
                if (self.center_text):
                    text_renderer.render_with_wrap(lines[i], self.get_x() + sx + 5 + ( (width - 10) / 2), self.get_y() + sy + 3 + (i * 20), self.text_color, align = "center")
                else:
                    text_renderer.render_with_wrap(lines[i], self.get_x() + sx + 5, self.get_y() + sy + 3 + (i * 20), self.text_color)

        # We'll display the tooltip on a letter-by-letter basis
        else:

            # Handle the cursor
            self.cursor_wait += 1
            if (self.cursor_wait >= 3):
                self.cursor_wait = 0

                self.cursor += 1
                if (self.cursor > len(self.text)):
                    self.cursor = len(self.text)

            # Loop through each line as normal...
            for i in range(0, len(lines)):

                # We're going to find out the length of each line up to and
                # including the current line.
                previous_length = 0

                for j in range(0, i + 1):
                    previous_length += len(lines[j])

                    # For any line other than the first line, we need to
                    # account for the \n character.
                    if (j > 0):
                        previous_length += 1

                # Now let's get to drawing the tooltip!
                # If the cursor has passed this line entirely, then just draw it.
                if (self.cursor >= previous_length):
                    if (self.center_text):
                        text_renderer.render_with_wrap(lines[i], self.get_x() + sx + 5 + ( (self.get_width() - 10) / 2), self.get_y() + sy + 3 + (i * 20), self.text_color, align = "center")
                    else:
                        text_renderer.render_with_wrap(lines[i], self.get_x() + sx + 5, self.get_y() + sy + 3 + (i * 20), self.text_color)

                # Otherwise... if the cursor is on this very line...
                # We will figure out how much of the line we want to draw.
                elif (self.cursor > (previous_length - len(lines[i]))):
                    string = sub_str(self.text, previous_length - len(lines[i]), self.cursor).replace("\n", "")

                    if (self.center_text):
                        text_renderer.render_with_wrap(string, self.get_x() + sx + 5 + ( (self.get_width() - 10) / 2), self.get_y() + sy + 3 + (i * 20), self.text_color, align = "center")
                    else:
                        text_renderer.render_with_wrap(string, self.get_x() + sx + 5, self.get_y() + sy + 3 + (i * 20), self.text_color)

class Dropdown(Element):

    def __init__(self, x, y, width, height, numrows = 3):

        Element.__init__(self, "dropdown", x, y, width, height)

        # How many rows appear in the dropdown at a given time?
        self.numrows = numrows

        # Store the dropdown options
        self.rows = []

        # Active selection?
        self.selection = None

        # Store the scroll offset
        self.offset = 0

        # Track dropdown section's visibility
        self.show_dropdown = False


        self.beforechange_events = []
        self.onchange_events = []


        # Scroll through the list when necessary
        self.scrollbar = Scrollbar(0, 0, 6, (self.height * self.numrows), 0, 0, 1).configure({
            "bloodline": self.get_bloodline()
        })


    # Dropdown always as high as a line of text, just one line
    def report_widget_height(self, text_renderer):

        #print self.height
        return text_renderer.font_height


    def on_focus(self):

        if (self.scrollbar):

            self.scrollbar.configure({
                "bloodline": self.get_bloodline()
            })


    def on_blur(self):

        if (self.scrollbar):

            self.scrollbar.configure({
                "bloodline": self.get_bloodline()
            })


    # Get current selection value
    def get_value(self):

        if (self.selection):

            return self.selection["value"]

        else:

            return ""


    def select(self, title):

        # Events resulting from selecting an option
        results = EventQueue()

        # Check all row data to find the first value match...
        for r in self.rows:

            if (r["title"] == title):

                # Raise any beforechange event...
                results.append(
                    self.raise_action("beforechange")
                )

                self.selection = r

                # Raise on-change events
                results.append(
                    self.raise_action("change")
                )

        # Return events
        return results


    # Select previous value (i.e. mouse wheel scroll)
    def select_previous(self):

        # Events that result from changing the selection
        results = EventQueue()

        # Find the index of the current selection
        for i in range( 0, len(self.rows) ):

            # Match?
            if ( self.selection == self.rows[i] ):

                # We want the previous one...
                previous_index = (i - 1)

                # Stay in bounds; don't wrap.
                if (previous_index >= 0):

                    # Select the previous index by its value
                    results.append(
                        self.select_by_value(
                            self.rows[previous_index]["value"]
                        )
                    )

                    # Return results immediately
                    return results

        # We must not have changed the selection after all
        return results


    # Select next value (i.e. mouse wheel scroll)
    def select_next(self):

        # Events that result from changing the selection
        results = EventQueue()

        # Find the index of the current selection
        for i in range( 0, len(self.rows) ):

            # Match?
            if ( self.selection == self.rows[i] ):

                # We want the next one...
                next_index = (i + 1)

                # Stay in bounds; don't wrap.
                if (next_index < len(self.rows)):

                    # Select the next index by its value
                    results.append(
                        self.select_by_value(
                            self.rows[next_index]["value"]
                        )
                    )

                    # Return results immediately
                    return results

        # We must not have changed the selection after all
        return results


    def select_by_value(self, value):

        # Events that result from selecting the given value
        results = EventQueue()

        # Check all row data to find the first value match...
        for r in self.rows:

            if (r["value"] == value):

                results.append(
                    self.raise_action("beforechange")
                )

                results.append(
                    self.raise_action("change")
                )

                """
                # Raise any beforechange event...
                for e in self.beforechange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                self.selection = r

                """
                # Raise any onchange event...
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                #return True

        ## Well, if we're still here, then we couldn't find it.
        #return False

        # Return events
        return results


    # Select by index
    def select_by_row_index(self, index):

        # Events resulting from selecting an option
        results = EventQueue()

        # Sanity
        if ( index < len(self.rows) ):

            # Raise any beforechange event...
            results.append(
                self.raise_action("beforechange")
            )

            self.selection = self.rows[index]

            # Raise on-change events
            results.append(
                self.raise_action("change")
            )


            # Lastly, scroll to new index
            self.offset = index


        # Return events
        return results


    # Get the index of the current selection.
    # Return -1 if we have no rows.
    def get_current_row_index(self):

        # No rows?
        if ( len(self.rows) == 0 ):

            # Return -1 when we have no rows
            return -1

        else:

            # Loop rows
            for y in range( 0, len(self.rows) ):

                # Active row?
                if ( self.rows[y] == self.selection ):

                    # Return index
                    return y


            # We didn't find a currently selected row.
            # Assume 0, then.
            return 0


    # Find the first known index of a option starting with a given string.
    # Optional offset to skip n rows, with option to start at the top if starting in the middle.
    def find_first_row_index_starting_with_string(self, s, start = 0, loop = True):

        # Loop rows, with optional offset
        y = start


        # Loop through the last row
        while ( y < len(self.rows) ):

            # Does this row match?
            if ( self.rows[y]["title"].startswith(s) ):

                # Return the row index
                return y

            else:

                # Loop on
                y += 1


        # We didn't find a matching row.  Should we try to start at the top?
        if ( (start > 0) and (loop == True) ):

            # Try one more time...
            return self.find_first_row_index_starting_with_string(s)

        # No more searching
        else:

            # No match found
            return None


    def count(self):
        return len(self.rows)

    def get_scroll_max(self):
        return len(self.rows) - self.numrows

    def scroll_to(self, index):
        if (index + self.num_rows > len(self.row_data)):
            index = len(self.row_data) - self.num_rows

        if (index < 0):
            index = 0

        self.bounds = [index, index + self.num_rows]

        if (self.setter):
            self.setter(self.bounds[0])

    def has_mouse(self, offset):

        if (not self.is_visible()):
            return False

        self_has_mouse = intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height()) )

        return self_has_mouse

    def get_element_index(self, element):
        log( "?" )
        for i in range(0, len(self.row_data)):
            if (self.row_data[i] == element):
                return i

        return -1

    def get_element_index_offset(self, element):
        log( "?" )
        return self.get_element_index(element) - self.bounds[0]


    # Empty the dropdown, but preserve offset information
    def empty(self):

        # Clear row data
        self.rows = []

        # We'll have to clear the selection, too
        self.selection = None


    # Completely reset the dropdown
    def clear(self):

        self.rows = []
        self.offset = 0
        self.show_dropdown = False
        self.selection = None

    def add(self, title, value):

        self.rows.append({
            "title": title,
            "value": value
        })

        # Will we need a scrollbar?
        if (len(self.rows) > self.numrows):

            self.scrollbar.max_value = max(
                0,
                len(self.rows) - self.numrows
            )


        # Is this the default selection?
        if (self.selection == None):

            self.selection = {
                "title": title,
                "value": value
            }

    def toggle_dropdown(self):

        if (self.show_dropdown):
            self.show_dropdown = False
            self.offset = 0

        else:
            self.show_dropdown = True

    def draw(self, sx, sy, text_renderer, window_controller):

        # Render point
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y() + self.get_margin_top()
        )

        Widget.__std_render_border__( self, rx, ry, self.get_width(), self.get_render_height(text_renderer), window_controller, rounded = self.get_has_rounded_corners() )

        if (self.selection):
            text_renderer.render_with_wrap(self.selection["title"], rx + self.get_padding_left(), ry + self.get_padding_top(), self.get_color())

        # Size the little arrow at 50% of text height, then specify
        # that we'll render it centered-ish.
        arrow_size = int(text_renderer.font_height / 2)

        (rxArrow, ryArrow) = (
            rx + self.get_width() - int(2 * arrow_size),
            ry + int(0.5 * arrow_size) + self.get_padding_top()
        )

        draw_triangle(rxArrow, ryArrow, arrow_size, arrow_size, self.get_color(), None, DIR_DOWN)

        """
        # First, draw the active selection and the dropdown arrow
        if (self.active):

            draw_rect(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.height, self.background_active)
            draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.height, self.border_color_active, 2)

            # Here is the dropdown arrow...
            draw_rect(sx + self.get_x() + self.get_width() - self.height, sy + self.get_y(), self.height, self.height, self.background) # arrow background never changes...
            draw_rect_frame(sx + self.get_x() + self.get_width() - self.height, sy + self.get_y(), self.height, self.height, self.border_color_active, 2)

            padding = 8
            draw_triangle(sx + self.get_x() + self.get_width() - self.height + padding, sy + self.get_y() + padding, self.height - (2 * padding), self.height - (2 * padding), self.text_color_active, None, DIR_DOWN)

            if (self.selection):

                padding = 2

                r = (sx + self.get_x() + padding, sy + self.get_y(), self.get_width() - (padding * 2) - self.height, self.height)

                window_controller.get_scissor_controller().push(r)

                text_renderer.render_with_wrap(self.selection["title"], sx + self.get_x() + padding, sy + self.get_y() + padding, self.text_color_active)

                window_controller.get_scissor_controller().pop()

        else:

            draw_rect(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.height, self.background)
            draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), self.height, self.border_color, 2)

            # Here is the dropdown arrow...
            draw_rect_frame(sx + self.get_x() + self.get_width() - self.height, sy + self.get_y(), self.height, self.height, self.border_color, 2)

            padding = 8
            draw_triangle(sx + self.get_x() + self.get_width() - self.height + padding, sy + self.get_y() + padding, self.height - (2 * padding), self.height - (2 * padding), self.text_color, None, DIR_DOWN)

            if (self.selection):

                padding = 2

                r = (sx + self.get_x() + padding, sy + self.get_y(), self.get_width() - (padding * 2) - self.height, self.height)

                window_controller.get_scissor_controller().push(r)

                text_renderer.render_with_wrap(self.selection["title"], sx + self.get_x() + padding, sy + self.get_y() + padding, self.text_color)

                window_controller.get_scissor_controller().pop()
        """


    def render_overlays(self, sx, sy, text_renderer, window_controller):

        # Render point
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y() + self.get_margin_top()# + self.get_render_height(text_renderer) # Offset by height of base widget to render it "beneath" the base widget
        )


        # If necessary, render the dropdown selections
        if (self.show_dropdown):

            h = (self.get_render_height(text_renderer) * self.numrows)

            # Draw a background region
            """
            draw_rect_with_horizontal_gradient(rx, ry + self.get_render_height(text_renderer), self.get_width(), h, self.get_gradient_start(), self.get_gradient_end())
            draw_rect_frame(sx + self.get_x(), sy + self.get_y() + self.height, self.get_width(), h, self.border_color, 2)
            """
            Widget.__std_render_border__( self, rx, ry + self.get_render_height(text_renderer), self.get_width(), h, window_controller, rounded = self.get_has_rounded_corners() )

            # Render each option from the current offset...
            pos = self.offset

            if (pos + self.numrows >= len(self.rows)):
                pos = len(self.rows) - self.numrows

                if (pos < 0):
                    pos = 0

            padding = 2

            # Dropdown area available to render text to...
            r = (rx, ry + self.get_render_height(text_renderer), self.get_width(), h)

            mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

            # If the scrollbar is needed...
            if (len(self.rows) > self.numrows):
                r = offset_rect(r, w = -1 * int(text_renderer.font_height / 2))

            window_controller.get_scissor_controller().push(r)

            for y in range(pos, min(pos + self.numrows, len(self.rows))):

                lr = (rx, ry + self.get_render_height(text_renderer) + (y * self.get_render_height(text_renderer)), self.get_width() - (padding * 0), (self.get_render_height(text_renderer)))

                #if (intersect(mr, lr)):
                #    window_controller.get_scissor_controller().pop()

                text_renderer.render_with_wrap(self.rows[y]["title"], rx + self.get_padding_left(), ry + self.get_padding_top() + self.get_render_height(text_renderer) + ( (y - pos) * self.get_render_height(text_renderer) ), self.get_color())

                #if (intersect(mr, lr)):
                #    window_controller.get_scissor_controller().push(r)

                # Trailing border
                #draw_rect(sx + self.get_x() + padding, sy + self.get_y() + self.height + ( (y - pos) * self.height ) + self.height - (padding / 2), (self.get_width() - (2 * padding)), padding, self.border_color)

            window_controller.get_scissor_controller().pop()


            # Does the dropdown require the scrollbar?
            if (len(self.rows) > self.numrows):

                self.scrollbar.draw(rx + self.get_width() - self.scrollbar.get_width(), ry + self.get_render_height(text_renderer), text_renderer, window_controller)


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Make sure scrollbar exists
        if (self.scrollbar):

            # **Hack
            self.scrollbar.height = (self.get_render_height(text_renderer) * self.numrows)


        # Events that rsult from processing the dropdown
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        results.append(
            self.scrollbar.process(sx + self.get_x() + self.get_width() - self.scrollbar.get_width(), sy, text_renderer, control_center, masked, system_input, mouse, parent)
        )

        #if (intersect( (self.get_x() + sx, self.get_y() + sy, self.get_width(), height), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):
        #    if (mouse["scrolled"] == "up"):
        #        self.scroll_to(self.bounds[0] - 1)
        #   elif (mouse["scrolled"] == "down"):
        #        self.scroll_to(self.bounds[0] + 1)

        if (not self.show_dropdown):

            h = self.get_render_height(text_renderer)#min(self.entry_height * self.num_rows, self.entry_height * len(self.row_data))

            if ( (not masked) and (intersect( (self.get_x() + sx, self.get_y() + sy, self.get_width(), h), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)) ) ):

                # Mark as having mouse
                self.processed_mouse = True

                # If not last time, focus on dropdown
                if (not self.processed_mouse_last_time):

                    # Focus
                    self.focus()


                # Toggle dropdown on click
                if (mouse["clicked"]):

                    self.toggle_dropdown()


                # Wheel scroll to tick selection?
                elif (mouse["scrolled"] == "up"):

                    results.append(
                        self.select_previous()
                    )


                elif (mouse["scrolled"] == "down"):

                    results.append(
                        self.select_next()
                    )


            else:

                # Flag as not having mouse
                self.processed_mouse = False

                # If we had the mouse last time, call for a blur
                if (self.processed_mouse_last_time):

                    # Blur
                    self.blur()


        else:

            render_height = self.get_render_height(text_renderer)

            mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

            # Entire area
            rAll = (sx + self.get_x(), sy + self.get_y(), self.get_width(), render_height + (self.numrows * render_height))

            # Current selection area
            rSelection = (sx + self.get_x(), sy + self.get_y(), self.get_width(), render_height)

            # Entire dropdown area
            rDropdown = (sx + self.get_x(), sy + self.get_y() + render_height, self.get_width(), (self.numrows * render_height))

            # Dropdown area available to click
            rDropdownClickable = (sx + self.get_x(), sy + self.get_y() + render_height, self.get_width(), (self.numrows * render_height))

            # Scrollbar area
            rDropdownScrollbar = (sx + self.get_x() + self.get_width() - (render_height / 2), sy + self.get_y() + render_height, 0, (self.numrows * render_height))


            # If the scrollbar is needed...
            if (len(self.rows) > self.numrows):

                rDropdownClickable = offset_rect(rDropdownClickable, w = -1 * int(render_height / 2))
                rDropdownScrollbar = offset_rect(rDropdownScrollbar, w = int(render_height / 2))


            # Active?
            self.active = False

            if (intersect(rAll, mr) and (not masked)):

                self.active = True

                # Wheel scroll?
                if (mouse["scrolled"] == "up"):

                    self.offset -= 3

                    if (self.offset < 0):
                        self.offset = 0

                    self.scrollbar.set_value(self.offset)

                elif (mouse["scrolled"] == "down"):

                    self.offset += 3

                    if (self.offset >= len(self.rows) - self.numrows):

                        self.offset = len(self.rows) - self.numrows

                        if (self.offset < 0):
                            self.offset = 0

                    self.scrollbar.set_value(self.offset)


                # Hovering over current selection value?
                if (intersect(rSelection, mr)):

                    if (mouse["clicked"]):
                        self.show_dropdown = False

                # Hovering over a dropdown selection?
                elif (intersect(rDropdownClickable, mr)):

                    if (mouse["clicked"]):

                        y = self.offset + int( (mr[1] - rDropdownClickable[1]) / render_height )

                        if (y < len(self.rows)):

                            results.append(
                                self.raise_action("beforechange")
                            )

                            # We have a new selection...
                            self.selection = self.rows[y]

                            results.append(
                                self.raise_action("change")
                            )



                            """
                            # Raise any beforechange event...
                            for e in self.beforechange_events:
                                self.pending_events.append({
                                    "event-info": e,
                                    "parent": None,
                                    "params": {"dropdown-value": self.get_value()}
                                })

                            # Check for onchange events
                            for e in self.onchange_events:
                                self.pending_events.append({
                                    "event-info": e,
                                    "parent": None,
                                    "params": {"dropdown-value": self.get_value()}
                                })
                            """

                        # Hide the dropdown now that we've made a selection...
                        self.show_dropdown = False

                # Hovering over scrollbar?
                elif (intersect(rDropdownScrollbar, mr)):

                    self.scrollbar.process(sx + self.get_x() + self.get_width() - text_renderer.font_height, sy + self.get_y(), text_renderer, control_center, (rDropdownScrollbar[0], rDropdownScrollbar[1]), masked, system_input, mouse)

                    # Synchronize with the scroll bar...
                    self.offset = self.scrollbar.get_value()



                # Always check for keyboard input, scrolling to first alphabetical match
                keyboard_buffer = system_input["key-buffer"]

                if (len(keyboard_buffer) > 0):

                    log( "buffer:  ", keyboard_buffer )


                    # Get current index
                    index = self.get_current_row_index()

                    # Try to find the next item that starts with the first letter pressed
                    next_index = self.find_first_row_index_starting_with_string( "%s" % keyboard_buffer[0], start = index + 1, loop = True )

                    # Make sure we found a match
                    if (next_index):

                        # Select by index
                        results.append(
                            self.select_by_row_index(next_index)
                        )


            if ( mouse["clicked"] ):
                self.show_dropdown = False

            # In the end, does this element mask others below it?
            if ( ( not masked ) and ( intersect(rAll, mr) ) ):

                # Flag as having mouse
                self.processed_mouse = True

                # If not last time, focus...
                if (not self.processed_mouse_last_time):

                    # Focus
                    self.focus()


            else:

                # Flag as not having mouse
                self.processed_mouse = False

                # If we had it last time, then let's blur
                if (self.processed_mouse_last_time):

                    # Blur
                    self.blur()

        # Return resultant events
        return results


class Listbox(Element):

    def __init__(self, x, y, width, height, numrows = 3, on_click = ""):

        Element.__init__(self, "listbox", x, y, width, height)


        # How many rows appear in the dropdown at a given time?
        self.numrows = numrows

        # Store the dropdown options
        self.rows = []

        # Active selection?
        self.selection = None

        # Store the scroll offset
        self.offset = 0

        # Should this listbox expand to include all items?
        self.expand = False


        # The event we will fire when the user clicks on the listbox.
        # We'll also inject the current value as a param.
        self.on_click = on_click


        #self.on_change = p_on_change

        #self.beforeclick_events = []
        #self.onclick_events = []
        #self.onchange_events = []


        # Scroll through the list when necessary
        self.scrollbar = Scrollbar(0, 0, int(self.height / 2), (self.height * self.numrows))


    # Configure
    def configure(self, options):

        if ( "expand" in options ):
            self.expand = ( int( options["expand"] ) == 1 )


        # For chaining
        return self


    # Overwrite
    def configure_alpha_controller(self, options):

        # Standard configuration
        Widget.configure_alpha_controller(self, options)

        # Forward to children
        for row in self.rows:

            # Cascade
            row["widget"].configure_alpha_controller(options)


    # The listbox's height is the sum of the height required to render each member widget
    def report_widget_height(self, text_renderer):

        return sum( row["widget"].get_box_height(text_renderer) for row in self.rows )


    # Forward updated css state to list elements on focus
    def on_focus(self):

        # Loop rows
        for row in self.rows:

            # Update bloodline for children
            row["widget"].css({
                "bloodline": self.get_bloodline()
            })

            row["widget"].on_focus()


    # Forward updated css state to list elements on blur
    def on_blur(self):

        # Loop rows
        for row in self.rows:

            # Update each child's bloodline
            row["widget"].css({
                "bloodline": self.get_bloodline()
            })

            row["widget"].on_blur()


    def on_show(self, target, animated, on_complete):

        for row in self.rows:

            row["widget"].show(target, animated, on_complete)


    def on_hide(self, target, animated, on_complete):

        for row in self.rows:

            row["widget"].hide(target, animated, on_complete)


    def select(self, title):

        # Check all row data to find the first value match...
        for i in range(0, len(self.rows)):

            r = self.rows[i]

            if (r["title"] == title):

                # Raise any beforeclick event...
                results.append(
                    self.raise_action("preclick")
                )
                """
                for e in self.beforeclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                self.selection = r

                # Update offset
                self.offset = 0

                if (i >= self.numrows):
                    self.offset = (self.numrows - i)


                # Raise any onclick event...
                results.append(
                    self.raise_action("click")
                )
                """
                for e in self.onclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                # Raise any onchange event...
                results.append(
                    self.raise_action("change")
                )
                """
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                return True

        # Well, if we're still here, then we couldn't find it.
        return False


    def select_by_value(self, value):

        # Events that result from selecting the given value
        results = EventQueue()

        # Check all row data to find the first value match...
        for i in range(0, len(self.rows)):

            r = self.rows[i]

            if (r["value"] == value):

                # Raise any beforeclick event...
                results.append(
                    self.raise_action("preclick")
                )
                """
                for e in self.beforeclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                self.selection = r

                # Update offset
                self.offset = 0

                if (len(self.rows) > self.numrows):
                    self.offset = i - self.numrows

                    if (self.offset < 0):
                        self.offset = 0

                    elif (self.offset >= len(self.rows) - self.numrows):
                        self.offset = len(self.rows) - self.numrows

                        if (self.offset < 0):
                            self.offset = 0

                # Synchronize the scrollbar
                self.scrollbar.set_value(self.offset)


                # Raise any onclick event...
                results.append(
                    self.raise_action("click")
                )
                """
                for e in self.onclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                # Raise any onchange event...
                results.append(
                    self.raise_action("change")
                )
                """
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })
                """

                #return True

        # Return events
        return results


    # Get the currently selected item's value
    def get_value(self):

        if (self.selection):

            return self.selection["value"]

        else:

            return ""


    # Count items in listbox
    def count(self):

        return len(self.rows)


    # Determine how many ticks the scrollbar can move.
    def get_scroll_max(self):

        # Let's not return a negative value...
        return max(
            0,
            len(self.rows) - self.numrows
        )


    def scroll_to(self, index):

        if (index + self.num_rows > len(self.row_data)):
            index = len(self.row_data) - self.num_rows

        if (index < 0):
            index = 0

        self.bounds = [index, index + self.num_rows]

        if (self.setter):
            self.setter(self.bounds[0])


    def has_mouse(self, offset):

        if (not self.is_visible()):
            return False

        self_has_mouse = intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height()) )

        return self_has_mouse

    def get_element_index(self, element):
        log( "?" )
        for i in range(0, len(self.row_data)):
            if (self.row_data[i] == element):
                return i

        return -1

    def get_element_index_offset(self, element):
        log( "?" )
        return self.get_element_index(element) - self.bounds[0]

    def clear(self):
        self.rows = []
        self.offset = 0
        self.selection = None

    def add(self, title, value):

        self.rows.append({
            "widget": Button(title, 0, 0, self.get_width(), self.height).css({
                "bloodline": self.get_bloodline()
            }),
            "value": value
        })

        #self.rows[-1]["widget"].blur()

        # Will we need a scrollbar?
        if (len(self.rows) > self.numrows):

            self.scrollbar.max_value = max(
                0,
                len(self.rows) - self.numrows
            )


        # Is this the default selection?
        if (self.selection == None):

            self.selection = {
                "title": title,
                "value": value
            }


    # Add a separator to the listbox
    def add_separator(self):

        self.rows.append({
            "widget": Rectangle(0, 0, self.get_width(), 2).css({
                "bloodline": self.get_bloodline()
            }),
            "value": None # Separators don't do anything when clicked
        })

        #self.rows[-1]["widget"].blur()


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing this listbox
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        # Initial offset point
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )
        # Run processing on each child widget
        #for row in self.rows:
        for y in range( 0, len(self.rows) ):

            # Convenience
            row = self.rows[y]

            results.append(
                row["widget"].process(rx, ry, text_renderer, control_center, masked, system_input, mouse, parent = self)
            )

            # Advance offset cursor
            ry += row["widget"].get_box_height(text_renderer)

        mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

        # Entire area
        rAll = (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.report_widget_height(text_renderer))

        # Dropdown area available to click
        rDropdownClickable = (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.report_widget_height(text_renderer))

        # Scrollbar area
        rDropdownScrollbar = (sx + self.get_x() + self.get_width() - (self.height / 2), sy + self.get_y(), 0, self.report_widget_height(text_renderer))


        # If the scrollbar is needed...
        if ( ( not self.expand ) and ( len(self.rows) > self.numrows ) ):

            # Can't click list items on the right edge; the right edge needs a scrollbar.
            rDropdownClickable = offset_rect(rDropdownClickable, w = -1 * int(self.height / 2))

            # The scrollbar rectangle now has a defined width
            rDropdownScrollbar = offset_rect(rDropdownScrollbar, w = int(self.height / 2))


        # Active?
        self.active = False

        if (intersect(rAll, mr) and (not masked)):

            # Flag overall listbox as having mouse
            self.processed_mouse = True

            # If not last time, give focus
            if (not self.processed_mouse_last_time):

                # Focus
                self.focus()


            # Wheel scroll?
            if (mouse["scrolled"] == "up"):

                self.offset -= 1

                if (self.offset < 0):
                    self.offset = 0

                self.scrollbar.set_value(self.offset)

            elif (mouse["scrolled"] == "down"):

                self.offset += 1

                if (self.offset >= len(self.rows) - self.numrows):
                    self.offset = len(self.rows) - self.numrows

                    if (self.offset < 0):
                        self.offset = 0

                self.scrollbar.set_value(self.offset)


            # Hovering over a selection?
            if (intersect(rDropdownClickable, mr)):

                if (mouse["clicked"]):

                    # Check for beforeclick events
                    results.append(
                        self.raise_action("preclick")
                    )
                    """
                    for e in self.beforeclick_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": {"dropdown-value": self.get_value()}
                        })
                    """

                    # Calculate the index of the element we have clicked on...
                    index = 0

                    # Validate that we have items
                    if ( len(self.rows) > 0 ):

                        # Default to visible rows in a scrolling listbox
                        row_range = range(
                            self.offset,
                            self.offset + self.numrows
                        )

                        # Expand to include all rows?
                        if (self.expand):

                            # Update range
                            row_range = range( 0, len(self.rows) )

                        # Calculate clicked index
                        index = max( i for i in row_range if sum( row["widget"].get_box_height(text_renderer) for row in self.rows[0 : i] ) <= (mr[1] - rDropdownClickable[1]) )

                        #print mr, rDropdownClickable
                        #print sum( row["widget"].get_box_height(text_renderer) for row in self.rows[0 : index] )
                        #print "\tindex = %d" % index
                        #return EventQueue()

                    y = self.offset + int( (mr[1] - rDropdownClickable[1]) / self.height )

                    if (index < len(self.rows)):

                        # We have a new selection...
                        self.selection = self.rows[index]

                    # Hide the dropdown now that we've made a selection...
                    self.show_dropdown = False


                    # Check for onclick events
                    results.append(
                        self.raise_action("click")
                    )

                    # Always add in a custom event based on this listbox's on-click event
                    results.inject_event(
                        EventQueueIter(
                            self.on_click,                      # The event to fire
                            {
                                "value": self.get_value()       # This listbox's currently selected value
                            }
                        )
                    )

                    """
                    for e in self.onclick_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": {"dropdown-value": self.get_value()}
                        })
                    """

                    # Check for onchange events...
                    results.append(
                        self.raise_action("change")
                    )
                    """
                    for e in self.onchange_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": {"dropdown-value": self.get_value()}
                        })
                    """

            # Hovering over scrollbar?
            elif (intersect(rDropdownScrollbar, mr)):

                self.scrollbar.process(text_renderer, control_center, (rDropdownScrollbar[0], rDropdownScrollbar[1]), masked, system_input, mouse)

                # Synchronize with the scroll bar...
                self.offset = self.scrollbar.get_value()

        else:

            # Flag as not having mouse
            self.processed_mouse = False

            # if we had it last time, we should blur now
            if (self.processed_mouse_last_time):

                # Blur
                self.blur()


        #if ( (not self.active) and (mouse["clicked"]) ):
        #    self.show_dropdown = False


        # Return resultant events
        return results


    # Render the listbox
    def draw(self, sx, sy, text_renderer, window_controller):

        # Render each visible item...
        h = self.report_widget_height(text_renderer)

        # Draw a background region
        Widget.__std_render_border__( self, sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_render_height(text_renderer), window_controller, rounded = self.get_has_rounded_corners() )
        #draw_rect(sx + self.get_x(), sy + self.get_y(), self.get_width(), h, (25, 25, 25))
        #draw_rect_frame(sx + self.get_x(), sy + self.get_y(), self.get_width(), h, (95, 95, 95), 2)

        # Render each option from the current offset...
        pos = self.offset

        if (pos + self.numrows >= len(self.rows)):
            pos = len(self.rows) - self.numrows

            if (pos < 0):
                pos = 0

        padding = 0

        # Dropdown area available to render text to...
        r = (sx + self.get_x() + padding, sy + self.get_y(), self.get_width() - (padding * 2), self.report_widget_height(text_renderer))

        mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

        # If the scrollbar is needed...
        if ( ( not self.expand ) and ( len(self.rows) > self.numrows ) ):
            r = offset_rect(r, w = -1 * int(self.height / 2))

        window_controller.get_scissor_controller().push(r)

        # Initial render point
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left(),
            sy + self.get_y() + self.get_padding_top()
        )

        # Default render range
        render_range = range(
            pos,
            min( pos + self.numrows, len(self.rows) )
        )

        # Render all?
        if (self.expand):

            render_range = range( 0, len(self.rows) )


        # Render according to render range...
        for y in render_range:

            lr = (rx, ry, self.get_width(), self.rows[y]["widget"].get_box_height(text_renderer))

            #if (self.rows[y] == self.selection):
            #    draw_rect(lr[0], lr[1], lr[2], lr[3], (75, 75, 75))


            if (0 and intersect(mr, lr)):
                window_controller.get_scissor_controller().pop()
                #text_renderer.render_with_wrap(self.rows[y]["title"] + " %s" % self.get_bloodline(), sx + self.get_x() + padding, sy + self.get_y() + ( (y - pos) * self.height ), (25, 225, 25))
                self.rows[y]["widget"].draw(sx + self.get_x(), sy + self.get_y() + ( (y - pos) * self.height ), text_renderer, window_controller)
                window_controller.get_scissor_controller().push(r)

            else:
                #text_renderer.render_with_wrap(self.rows[y]["title"], sx + self.get_x() + padding, sy + self.get_y() + ( (y - pos) * self.height ), (225, 225, 25))
                self.rows[y]["widget"].draw(rx, ry, text_renderer, window_controller)


            # Advance cursor
            ry += self.rows[y]["widget"].get_box_height(text_renderer)

            # Trailing border
            #draw_rect(sx + self.get_x() + padding, sy + self.get_y() + self.height + ( (y - pos) * self.height ) + self.height - (padding / 2), (self.get_width() - (2 * padding)), padding, self.border_color)

        window_controller.get_scissor_controller().pop()


        # Does the dropdown require the scrollbar?
        if ( ( not self.expand ) and ( len(self.rows) > self.numrows ) ):

            self.scrollbar.draw( sx + self.get_x() + self.get_width() - int(self.height / 2), sy + self.get_y(), text_renderer, window_controller)


class Treeview(Element):

    def __init__(self, x, y, width, height, row_height, is_root = True, parent = None):#, background = None, background_active = None, border_color = None, border_color_active = None, text_color = None, text_color_active = None, root = True):

        Element.__init__(self, "treeview", x, y, width, height)


        # Height per row?
        self.row_height = row_height


        # Is this the root of the tree, or a child branch?
        self.is_root = is_root

        # If it's not the root, we'll want to remember the parent for back-referencing
        self.parent = parent


        # Store the dropdown options
        self.rows = []

        # Scrolling offset (row by row)
        self.row_offset = 0

        """
        # Each branch can have a tooltip
        self.tooltip_width = 360
        self.tooltip = Tooltip(background = (25, 25, 25, 0.8), border_color = (225, 225, 225), text_color = (215, 215, 215), width = self.tooltip_width, hover = "instant")

        self.last_hovered = None
        self.hover_delay = None

        self.onclick_events = []
        self.onchange_events = []
        """

        self.last_hovered = None
        self.hover_delay = None


    # Report tree height.  Varies depending on children, branch toggle status, etc.
    def report_widget_height(self, text_renderer):

        # Tally
        height = 0

        # Loop rows
        for row in self.rows:

            # Each branch on the root level (for this given tree) is always visible
            height += self.row_height#row["element"].report_widget_height(text_renderer)

            # If it's toggled to show, then we add in the height of the nested tree
            if (row["toggled"]):

                # Add in the height of the child tree
                height += row["children"].report_widget_height(text_renderer)

        # Return total
        return height


    # Count the number of branches inis tree (including children)
    def count(self):

        # Tally
        total = 0

        # Loop children
        for r in self.rows:

            # +1
            total += 1

            # +child's children
            total += r["children"].count()

        # Return sum
        return total


    # Count the number of currently visible branches.  I believe we can use this for various rendering calcluations?
    def count_visible(self):

        # Tally
        total = 0

        # Loop all rows
        for r in self.rows:

            # Root is always visible, if nothing else?
            total += 1

            # Add in children
            if (r["toggled"]):

                # Add in child count
                total += r["children"].count_visible()

        # Return sum
        return total


    def fetch_events(self, alias = None):

        events = []
        events.extend(self.pending_events)

        for e in events:
            e["parent"] = alias

        for r in self.rows:
            events.extend(r["children"].fetch_events(alias))

        # Now clear all of those pending events...
        self.pending_events = []

        return events


    def compile_xml_string(self, prefix = ""):

        xml = ""

        for row in self.rows:

            if (row["children"].count() > 0):

                xml += prefix + "<event"# type = '" + row["params"]["type"] + "' "

                for p in row["params"]:
                    xml += " %s = '%s'" % (p, row["params"][p].replace("'", "&apos;"))

                xml += ">" + "\n"

                xml += row["children"].compile_xml_string(prefix + "\t") + "\n"

                xml += prefix + "</event>" + "\n"

            else:

                xml += prefix + "<event"

                for p in row["params"]:
                    xml += " %s = '%s'" % (p, row["params"][p].replace("'", "&apos;"))

                xml += " />" + "\n"

        return xml


    # Ge tthe maximum number of scroll ticks a potential scrollbar can move for this treeview
    def get_scroll_max(self):

        # Don't return negative values
        return max(
            0,
            len(self.rows) - self.numrows
        )


    def has_mouse(self, sx, sy):

        log( 5/0 )

        if (not self.is_visible()):
            return False

        self_has_mouse = intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (sx + self.get_x(), sy + self.get_y(), self.get_width(), self.get_height()) )

        return self_has_mouse

    def get_tooltip(self):

        if (self.hover_delay == 0):
            return self.tooltip

        else:

            for r in self.rows:
                tooltip = r["children"].get_tooltip()

                if (tooltip):
                    return tooltip

        return None

    def get_element_index(self, element):
        log( "?" )
        for i in range(0, len(self.row_data)):
            if (self.row_data[i] == element):
                return i

        return -1

    def get_element_index_offset(self, element):
        log( "?" )
        return self.get_element_index(element) - self.bounds[0]


    # Reset all content in the treeview
    def clear(self):

        # Erase rows
        self.rows = []

        # Mark is not expanded, i guess
        self.toggled = False


    # Add a new leaf to the tree
    def add(self, elem, params, tooltip, parent = None):

        # Add to the rows, using a hash format so we can track flags on the row
        self.rows.append({
            "element": elem,
            "params": params,

            "tooltip": tooltip,
            "tooltip-delay": TOOLTIP_DELAY,

            "toggled": False,                                                                       # Default to not expanded

            "children": Treeview(0, 0, self.get_width(), self.height, self.row_height, is_root = False, parent = self).configure({   # Create a nested treeview in case this new branch wants children of its own
                "bloodline": self.get_bloodline()
            })
        })


        # Return the new branch
        return ( len(self.rows) - 1 )


    # Add a child to a given branch in this tree
    def add_to_branch(self, index, elem, params, tooltip):

        # The "children" key points to the tree we set up when we created this branch
        self.rows[index]["children"].add(elem, params, tooltip)

        # I guess we'll expand this branch now...
        self.rows[index]["toggled"] = True


        # Return the new branch
        return ( len(self.rows[index]["children"].rows) - 1 )


    def process(self, sx, sy, text_renderer, control_center, masked = False, system_input = {}, mouse = {}, parent = None):

        # Events that result from processing this treeview
        results = Element.process(self, sx, sy, text_renderer, control_center, masked, system_input, mouse, parent)

        result = False

        y = 0

        if (parent == None):
            y -= (self.row_offset * self.row_height)

        # Render point
        (rx, ry) = (
            sx + self.get_x(),
            sy + self.get_y()
        )

        mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

        draw_rect(mr[0], mr[1], mr[2], mr[3], (0, 255, 0))

        hover_item = None

        # Process each branch
        for i in range( 0, len(self.rows) ):

            # Convenience
            branch = self.rows[i]

            rClick = (rx, ry + y, self.get_width(), self.row_height)

            #draw_rect_frame(rClick[0], rClick[1], rClick[2], rClick[3], (0, 0, 255), 2)

            rButton = (rClick[0], rClick[1], self.row_height, self.row_height)

            # Check for mouse hover
            if ( (not masked) and (intersect(mr, rButton)) ):

                if (mouse["clicked"]):

                    branch["toggled"] = (not branch["toggled"])

                    branch["element"].focus()

                    # Force metric updates for the entire ancestry
                    parent_tree = self.parent

                    # Keep going higher
                    while (parent_tree):

                        # Force metric updates
                        parent_tree.focus()
                        parent_tree.invalidate_cached_metrics()

                        # Can you take me higher?
                        parent_tree = parent_tree.parent


            # Right-click on the row?
            if ( (not masked) and (intersect(mr, rClick)) and (mouse["rightclicked"]) ):

                results.add(
                    action = "fire-tree-rk",
                    params = {
                        "tree": self,
                        "row-index": i
                    }
                )

                """
                e = {
                    "action": "fire-tree-rk",
                    "target": None,
                    "param": branch
                }

                self.pending_events.append({
                    "event-info": e,
                    "parent": None,
                    "params": {}
                })
                """

            # Advance y cursor to the next row, irregardless...
            y += self.row_height


            # If this branch is toggled, we need to render any children as well...
            if (branch["toggled"]):

                # We'll end up advancing the y cursor by the amount of vertical space the child node requires...
                results.append(
                    branch["children"].process(rx + self.row_height, ry + y, text_renderer, control_center, masked, system_input, mouse, parent = self)
                )#(rClick[0] + self.row_height, rClick[1] + self.row_height)

                y += branch["children"].count_visible() * self.row_height

            # Otherwise, we do nothing...
            else:
                pass


        if (0):

            if (hover_item != self.last_hovered):

                self.last_hovered = hover_item
                self.hover_delay = 60

                self.tooltip.hide()

            elif (self.last_hovered != None):

                if (self.hover_delay > 0):
                    self.hover_delay -= 1

                else:
                    self.tooltip.set_text(self.last_hovered["tooltip"], text_renderer)

                    self.tooltip.x = 0
                    self.tooltip.y = 0

                    self.tooltip.show()


        # Return resultant events
        return results


    # Render the treeview
    def draw(self, sx, sy, text_renderer, window_controller, recursive = False):

        (mx, my) = pygame.mouse.get_pos()
        mr = (mx, my, 1, 1)

        y = 0

        if (not recursive):
            y -= (self.row_offset * self.row_height)

        oy = y

        #if (not recursive):
        #    window_controller.get_scissor_controller().push( (0, sy + self.get_y(), SCREEN_WIDTH, self.report_widget_height(text_renderer)) )

        # Render each branch
        for branch in self.rows:

            rClick = (sx + self.get_x(), sy + self.get_y() + y, self.get_width(), self.row_height)

            # First, render the row itself.  Start with a background...
            r = (sx + self.get_x(), sy + self.get_y() + y, self.get_width(), self.row_height)
            padding = 0

            #r = offset_rect(r, -padding, -padding, padding * 2, padding * 2)

            #color = self.get_gradient_start()#branch["element"].background
            #if (color):
            #    draw_rect(rClick[0], rClick[1], rClick[2], rClick[3], color)

            # Render a +/- toggle
            if (branch["toggled"]):

                inset = 4

                rButton = (rClick[0] + inset, rClick[1] + inset, self.row_height - (2 * inset), self.row_height - (2 * inset))

                color = self.get_border_color()

                # Perimeter
                draw_rect_frame(rButton[0], rButton[1], rButton[2], rButton[3], color, 1)

                # - sign
                (cx, cy) = (
                    rButton[0] + int(rButton[2] / 2),
                    rButton[1] + int(rButton[3] / 2)
                )

                line_radius = (self.row_height / 2) - 6

                draw_rect(cx - line_radius, cy - 1, (line_radius * 2), 2, color)

                # Trace line
                trace_length = (branch["children"].count_visible() * self.row_height)

                draw_rect(cx - 1, rButton[1] + rButton[3], 2, trace_length, color)
                draw_rect(rButton[0] + inset, rButton[1] + int(rButton[3] / 2), rButton[2] - (2 * inset), 2, color)
                #draw_rect(rButton[0] + int(rButton[2] / 2), rButton[1], 2, rButton[3], color)

                # Anchor lines
                ly = rButton[1] + rButton[3] + int(self.row_height / 2)

                for each in branch["children"].rows:

                    draw_rect(cx, ly - 1, int(rButton[2] / 2), 2, color)

                    ly += (1 + each["children"].count_visible()) * self.row_height
                    #ly += branch["children"].rows[each]["children"].count_visible() * self.row_height

            else:

                inset = 4

                rButton = (rClick[0] + inset, rClick[1] + inset, self.row_height - (2 * inset), self.row_height - (2 * inset))

                color = self.get_border_color()

                # Perimeter
                draw_rect_frame(rButton[0], rButton[1], rButton[2], rButton[3], color, 1)

                # + sign
                (cx, cy) = (
                    rButton[0] + int(rButton[2] / 2),
                    rButton[1] + int(rButton[3] / 2)
                )

                line_radius = (self.row_height / 2) - 6

                draw_rect(rButton[0] + inset, rButton[1] + int(rButton[3] / 2), rButton[2] - (2 * inset), 2, color)
                draw_rect(rButton[0] + int(rButton[2] / 2), rButton[1] + inset, 2, rButton[3] - (2 * inset), color)
                #draw_rect(cx - line_radius, cy - 1, (line_radius * 2), 2, color)
                #draw_rect(cx - 1, cy - line_radius, 2, (line_radius * 2), color)


            # Now render the element in this row
            branch["element"].draw( sx + self.get_x() + self.row_height, sy + self.get_y() + y, text_renderer, window_controller)


            # Advance y cursor to the next row, irregardless...
            y += self.row_height


            # If this branch is toggled, we need to render any children as well...
            if (branch["toggled"]):

                # We'll end up advancing the y cursor by the amount of vertical space the child node requires...
                y += branch["children"].draw( rClick[0] + self.row_height, rClick[1] + self.row_height, text_renderer, window_controller, recursive = True )

            # Otherwise, we do nothing...
            else:
                pass


        #if (self.hover_delay == 0):
        if (not recursive):#self.root == True):

            tooltip = self.get_tooltip()

            if (tooltip):

                (x, y) = (mx + 16, my + 16)

                if (x + self.tooltip_width > SCREEN_WIDTH):
                    x = mx - self.tooltip_width

                tooltip.draw(x, y, text_renderer, window_controller)


        #if (not recursive):
        #    window_controller.get_scissor_controller().pop()

        #text_renderer.render_with_wrap( "%d" % self.report_widget_height(text_renderer), sx + self.get_x(), sy + self.get_y(), (225, 225, 25) )
        #text_renderer.render_with_wrap( "%d" % self.count(), sx + self.get_x(), sy + self.get_y(), (225, 225, 25) )

        # Return the height we required for rendering this branch...
        return y
