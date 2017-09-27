from extensions.guiextensions import GUIWidgetPopulationFunctions

from code.utils.common import *
from code.render.glfunctions import *

from code.constants.common import CORNER_SIZE, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT


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


        # GUI events
        self.pending_events = []


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


    # Get all widgets of a given type
    def get_widgets_by_type(self, widget_type):

        # Matches
        results = []

        # Loop widgets
        for name in self.widgets:

            # Convenience
            widget = self.widgets[name]

            # Match?
            if ( widget.element_type == widget_type ):

                # Append
                results.append(widget)

        # Results
        return results


    # Render all widgets
    def draw_all(self, gui_text_renderer, p_offset, window_controller):

        # Loop in order added
        for name in self.widget_order:

            # Fetch widget
            widget = self.get_widget_by_name(name)

            # Validate
            if (widget):

                # Only render visible widgets
                if ( widget.is_visible() ):

                    # Render widget!
                    widget.draw(None, gui_text_renderer = gui_text_renderer, p_offset = p_offset, sprites = self.sprites, window_controller = window_controller)


    # Render only those widgets at a given z index
    def draw_z_index(self, gui_text_renderer, p_offset, z, window_controller):

        # Loop in order added
        for name in self.widget_order:

            # Fetch widget
            widget = self.get_widget_by_name(name)

            # Validate
            if (widget):

                # Only render visible widgets
                if ( widget.is_visible() ):

                    # Only render widgets that exist at the given z index
                    if (widget.z_index == z):

                        # Render widget!
                        widget.draw(None, gui_text_renderer = gui_text_renderer, p_offset = p_offset, sprites = self.sprites, window_controller = window_controller)


    # Process manager and all widgets
    def process(self, masked = False, gui_text_renderer = None, p_offset = (0, 0), system_input = {}, mouse = {}):

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
                if (widget.is_visible()):

                    masked |= widget.process(gui_text_renderer = gui_text_renderer, p_offset = p_offset, masked = masked, system_input = system_input, mouse = mouse)

                    # Get any pending events from the gui element...
                    self.pending_events.extend( widget.fetch_events(name) )


                    # If this widget possesses the mouse cursor at its current location, then no widget
                    # beneath this one can possibly respond to mouse clicks.
                    if (masked):

                        # No more click for you
                        mouse["clicked"] = False

        # Return whether or not any of the visible widgets contained the mouse cursor
        return masked


    # Add an event manually (e.g. hotkey)
    def add_event(self, event):

        # Append
        self.pending_events.append(event)


    # Return any events that need to take place
    def fetch_events(self):

        events = []
        events.extend(self.pending_events)

        # Now clear all of those pending events...
        self.pending_events = []

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
            int( node.get_attribute("x") ),
            int( node.get_attribute("y") ),
            int( node.get_attribute("width") ),
            int( node.get_attribute("height") ),
            background = params["background-color"],
            border_color = params["border-color"],
            has_rounded_corners = params["has-rounded-corners"],
            is_floating = ("floating" in node.attributes)
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
                #dialog.add_element(child_name, elem)
                dialog.gui_manager.add_widget_with_name(child_name, elem)

        dialog.show()

        return dialog


    def create_gui_element_from_xml_node(self, node, parent, control_center):

        #save_replay_dialog.add_element("n/a", Label("Save as:", (10, 10), text_color = (255, 255, 255)))

        gui_text_renderer = control_center.get_window_controller().get_text_controller_by_name("gui").get_text_renderer()


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

                    x = int(percent * parent.width)

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

                    y = int(percent * parent.height)

                # Raw y
                else:
                    y = int(y)

            else:
                y = 0


        (w, h) = (0, 0)

        if ( node.get_attribute("width") ):

            w = node.get_attribute("width")

            if (len(w) > 0):

                # Percentage-based width?
                if (w[-1] == "%"):
                    percent = int( w[0 : len(w)-1] ) / 100.0

                    w = int(percent * parent.width)

                # Raw width
                else:
                    w = int(w)


            else:
                w = 0

        if ( node.get_attribute("height") ):

            h = node.get_attribute("height")

            if (len(h) > 0):

                # Percentage-based height?
                if (h[-1] == "%"):
                    percent = int( h[0 : len(h)-1] ) / 100.0

                    h = int(percent * parent.height)

                # Raw height
                else:
                    h = int(h)

            else:
                h = 0





        # Special alignment?
        if ( node.get_attribute("align") ):

            if (node.get_attribute("align") == "center"):
                x -= (w / 2)

            elif (node.get_attribute("align") == "right"):
                x -= w


        # Generic label
        if (node.tag_type == "label"):

            elem = Label(
                node.get_attribute("value"),
                (x, y),
                text_color = params["text-color"],
                text_color_active = params["text-color-active"],
                align = "%s" % node.get_attribute("align")
            )

            elem.set_text(node.get_attribute("value"), gui_text_renderer)

            return elem

        # Text entry
        elif (node.tag_type == "entry"):

            elem = Text_Box(
                w, h,
                (x, y),
                border_color = params["border-color"],
                border_color_active = params["border-color-active"],
                background = params["background-color"],
                background_active = params["background-color-active"],
                text_color = params["text-color"],
                text_color_active = params["text-color-active"],
                has_rounded_corners = params["has-rounded-corners"]
            )

            return elem

        # Dropdown
        elif (node.tag_type == "dropdown"):

            elem = Dropdown(
                x, y, w, h,
                int( node.get_attribute("numrows") ),
                border_color = params["border-color"],
                border_color_active = params["border-color-active"],
                background = params["background-color"],
                background_active = params["background-color-active"],
                text_color = params["text-color"],
                text_color_active = params["text-color-active"]
            )

            # Get default dropdown options
            option_collection = node.get_nodes_by_tag("option")

            for ref_option in option_collection:
                elem.add( "%s" % ref_option.get_attribute("title"), "%s" % ref_option.get_attribute("value") )


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

            # Get any onchange event...
            onchange_collection = node.get_nodes_by_tag("onchange")

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

            return elem

        # Listbox
        elif (node.tag_type == "listbox"):

            elem = Listbox(
                x, y, w, h,
                int( node.get_attribute("numrows") ),
                border_color = params["border-color"],
                border_color_active = params["border-color-active"],
                background = params["background-color"],
                background_active = params["background-color-active"],
                text_color = params["text-color"],
                text_color_active = params["text-color-active"]
            )

            # Get default dropdown options
            option_collection = node.get_nodes_by_tag("option")

            for ref_option in option_collection:
                elem.add( "%s" % ref_option.get_attribute("title"), "%s" % ref_option.get_attribute("value") )

            # Get any beforeclick event
            beforeclick_collection = node.get_nodes_by_tag("beforeclick")

            for ref_beforeclick in beforeclick_collection:

                e = {
                    "action": "%s" % ref_beforeclick.get_attribute("event"),
                    "target": None,
                    "param": None
                }

                if (ref_beforeclick.get_attribute("target")):
                    e["target"] = ref_beforeclick.get_attribute("target")

                if (ref_beforeclick.get_attribute("param")):
                    e["param"] = ref_beforeclick.get_attribute("param")

                elem.beforeclick_events.append(e)

            # Get any onclick event...
            onclick_collection = node.get_nodes_by_tag("onclick")

            for ref_onclick in onclick_collection:

                e = {
                    "action": "%s" % ref_onclick.get_attribute("event"),
                    "target": None,
                    "param": None
                }

                if (ref_onclick.get_attribute("target")):
                    e["target"] = ref_onclick.get_attribute("target")

                if (ref_onclick.get_attribute("param")):
                    e["param"] = ref_onclick.get_attribute("param")

                elem.onclick_events.append(e)

            # Get any onchange event...
            onchange_collection = node.get_nodes_by_tag("onchange")

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

            return elem


        #save_replay_dialog.add_element("cancel-button", Button("Cancel", 80, 20, (10, 40), background = (25, 25, 25), background_active = (50, 50, 50), text_color_active = (37, 135, 255), border_color = (255, 255, 255), p_on_click = (self.cancel_save_replay,)))

        # Button
        elif (node.tag_type == "button"):

            elem = Button(
                "%s" % node.get_attribute("value"),
                w, h,
                (x, y),
                border_color = params["border-color"],
                border_color_active = params["border-color-active"],
                background = params["background-color"],
                background_active = params["background-color-active"],
                text_color = params["text-color"],
                text_color_active = params["text-color-active"],
                has_rounded_corners = params["has-rounded-corners"]
            )

            # Get any onclick events...
            onclick_collection = node.get_nodes_by_tag("onclick")

            for ref_onclick in onclick_collection:

                e = {
                    "action": "%s" % ref_onclick.get_attribute("event"),
                    "target": None,
                    "param": None
                }

                if (ref_onclick.get_attribute("target")):
                    e["target"] = ref_onclick.get_attribute("target")

                if (ref_onclick.get_attribute("param")):
                    e["param"] = ref_onclick.get_attribute("param")

                elem.onclick_events.append(e)


            # Get any onmouseover events...
            onmouseover_collection = node.get_nodes_by_tag("onmouseover")

            for ref_onmouseover in onmouseover_collection:

                e = {
                    "action": "%s" % ref_onmouseover.get_attribute("event"),
                    "target": None,
                    "param": None
                }

                if (ref_onmouseover.get_attribute("target")):
                    e["target"] = ref_onmouseover.get_attribute("target")

                if (ref_onmouseover.get_attribute("param")):
                    e["param"] = ref_onmouseover.get_attribute("param")

                elem.onmouseover_events.append(e)


            # Get any parameters
            param_collection = node.get_nodes_by_tag("param")

            for ref_param in param_collection:

                param_name = "%s" % ref_param.get_attribute("name")
                param_value = "%s" % ref_param.get_attribute("value")

                elem.params[param_name] = param_value


            return elem


        # Generic rectangle, used mostly as a separator
        elif (node.tag_type == "rect"):

            elem = Rectangle(
                w, h,
                params["background-color"],
                (x, y),
                False,
                None,
                params["has-rounded-corners"]
            )

            return elem

        # Hidden element for data tracking
        elif (node.tag_type == "hidden"):

            elem = Hidden(node.get_attribute("value"))

            return elem

        # Sub-dialog
        elif (node.tag_type == "dialog"):

            elem = Dialog(
                x, y, w, h,
                background = params["background-color"],
                background_active = params["background-color-active"],
                border_color = params["border-color"],
                has_rounded_corners = params["has-rounded-corners"],
                is_floating = ("floating" in node.attributes)
            )

            elem.z_index = 100

            # Get all of the dialog's children...
            child_collection = node.get_nodes_by_tag("*")

            for ref_child in child_collection:

                child_name = ""

                if (ref_child.get_attribute("name")):
                    child_name = ref_child.get_attribute("name")

                elem2 = self.create_gui_element_from_xml_node(ref_child, elem, control_center)

                if (elem2 != None):

                    elem.gui_manager.add_widget_with_name(child_name, elem2)

            return elem

        # Treeview
        elif (node.tag_type == "treeview"):

            elem = Treeview(
                x, y, w, h,
                row_height = params["row-height"],
                border_color = params["border-color"],
                border_color_active = params["border-color-active"],
                background = params["background-color"],
                background_active = params["background-color-active"],
                text_color = params["text-color"],
                text_color_active = params["text-color-active"]
            )

            return elem

        return None

# Element is the base class for a GUI element; it has color properties,
# show/hide methods, and things like that; all elements will have these properties.
class Element:
    def __init__(self, p_coords=(0, 0),
                       background = None,
                       background_active = None,
                       border_color = None,
                       border_color_active = None,
                       text_color = None,
                       text_color_active = None,
                       has_rounded_corners = False):

        self.visible = True
        self.active = False

        self.z_index = 0

        self.coords = p_coords

        self.child = None

        self.background = background
        self.background_active = background_active
        self.border_color = border_color
        self.border_color_active = border_color_active
        self.text_color = text_color
        self.text_color_active = text_color_active

        self.current_background = background
        self.current_border_color = border_color

        self.has_rounded_corners = has_rounded_corners

        """
        if (not self.background):
            self.background = (13, 11, 33)
        if (not self.background_active):
            self.background_active = (79, 64, 192)

        if (not self.border_color):
            self.border_color = (117, 90, 255)
        if (not self.border_color_active):
            self.border_color_active = (200, 200, 200)

        if (not self.text_color):
            self.text_color = (240, 240, 240)
        if (not self.text_color_active):
            self.text_color_active = (126, 255, 0)
        """

        self.pending_events = []

    def fetch_events(self, alias = None):
        events = []
        events.extend(self.pending_events)

        for e in events:
            e["parent"] = alias

        self.pending_events = []

        return events

    def set_coords(self, p_x, p_y):
        self.coords = (p_x, p_y)

    def get_visible_height(self):
        return self.height

    def process(self, remove = 0, me = 0, later = 0, masked = 0, system_input = {}, mouse = {}, gui_text_renderer = None, p_offset = None, parent = None):
        return False

    def deactivate(self):
        self.active = False

    # Overwrite these when necessary ############
    def get_width(self):
        return 0

    def get_height(self):
        return 0
    #############################################

    def show(self):
        self.visible = True

        if (self.child):
            self.child.show()

    def hide(self):
        self.visible = False

        if (self.child):
            self.child.hide()

    def is_visible(self):
        return self.visible

    def has_mouse(self, p_offset=(0, 0)):
        self_has_mouse = self.is_visible() and intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height()) )
        child_has_mouse = False

        if (self.child):
            child_has_mouse = self.child.is_visible() and self.child.has_mouse((0, 0))# (self.get_width() + p_offset[0], p_offset[1]) )

        return (self_has_mouse or child_has_mouse)

    def render_background(self, gui_text_renderer, p_offset=(0,0), sprites = None):

        if (self.has_rounded_corners):

            background_color = self.background
            if (self.active):
                background_color = self.background_active

            border_color = self.border_color
            if (self.active):
                border_color = self.border_color_active


            draw_rounded_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), background_color, border_color)

        else:

            if (self.active):

                if (self.background):
                    draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.get_visible_height(), self.background_active)

                if (self.border_color_active):
                    draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.get_visible_height(), self.border_color_active, 1)

            else:

                if (self.background):
                    draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.get_visible_height(), self.background)

                if (self.border_color):
                    draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.get_visible_height(), self.border_color, 1)

class CountboxObselete(Element):
    def __init__(self, p_coords=(0,0)):
        Element.__init__(self, p_coords)
        self.element_type = "Countbox"

        self.value = 0

        self.width = 72
        self.height = 32

        self.mouse_up = 1

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_value(self):
        return self.value

    def increase(self):
        self.value += 1
        if (pygame.key.get_pressed()[K_LCTRL]):
            self.value += 9

    def decrease(self):
        if (self.value > 0):
            self.value -= 1

        if (pygame.key.get_pressed()[K_LCTRL]):
            self.value -= 9
            if (self.value < 0):
                self.value = 0

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):
        draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), (0, 0, 0))
        draw_rect(p_offset[0] + self.coords[0] + 24, p_offset[1] + self.coords[1], 24, self.get_height(), (255, 255, 255))
        draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), (109, 129, 183), 1)

        rect_decrease = (p_offset[0] + self.coords[0] + 1, p_offset[1] + self.coords[1], 24, self.get_height())
        rect_increase = (p_offset[0] + self.coords[0] + 49, p_offset[1] + self.coords[1], 24, self.get_height())

        draw_rect_frame(rect_decrease[0], rect_decrease[1], rect_decrease[2], rect_decrease[3], (109, 129, 183), 1)
        draw_rect_frame(rect_increase[0], rect_increase[1], rect_increase[2], rect_increase[3], (109, 129, 183), 1)

        gui_text_renderer.render_with_wrap("%d" % self.value, p_offset[0] + self.coords[0] + (self.width / 2), p_offset[1] + self.coords[1], (0, 0, 0), align = "center")

        gui_text_renderer.render_with_wrap("-", p_offset[0] + self.coords[0] + 12, p_offset[1] + self.coords[1], (255, 255, 255), align = "center")
        gui_text_renderer.render_with_wrap("+", p_offset[0] + self.coords[0] + 60, p_offset[1] + self.coords[1], (255, 255, 255), align = "center")

        pos_mouse = pygame.mouse.get_pos()

        # Check decrease button
        result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), rect_decrease )
        if (result and (not intersect_any( (pos_mouse[0], pos_mouse[1], 1, 1), self.blacklist))):

            # Draw a border to signify the mouseover
            draw_rect_frame(rect_decrease[0], rect_decrease[1], rect_decrease[2], rect_decrease[3], (255, 255, 255), 1)

            # If the mouse isn't being clicked, we re-allow a new later mouse click
            if (not pygame.mouse.get_pressed()[0]):
                self.mouse_up = 1

            if (pygame.mouse.get_pressed()[0] and self.mouse_up == 1):
                self.mouse_up = 0

                self.decrease()

        else:
            if (not pygame.mouse.get_pressed()[0]):
                self.mouse_up = 1

        # Check increase button
        result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), rect_increase )
        if (result and (not intersect_any( (pos_mouse[0], pos_mouse[1], 1, 1), self.blacklist))):

            # Draw a border to signify the mouseover
            draw_rect_frame(rect_increase[0], rect_increase[1], rect_increase[2], rect_increase[3], (255, 255, 255), 1)

            # If the mouse isn't being clicked, we re-allow a new later mouse click
            if (not pygame.mouse.get_pressed()[0]):
                self.mouse_up = 1

            if (pygame.mouse.get_pressed()[0] and self.mouse_up == 1):
                self.mouse_up = 0

                self.increase()

        else:
            if (not pygame.mouse.get_pressed()[0]):
                self.mouse_up = 1

class Slider(Element):
    def __init__(self, p_text, p_width, p_height, p_coords=(0,0), p_min_value=0, p_max_value=100, p_multiple=1, p_on_change = None):
        Element.__init__(self, p_coords)
        self.element_type = "Slider"

        self.text = p_text

        self.value = p_max_value

        self.width = p_width
        self.height = p_height

        self.shade = (0, 100, 0)

        self.min_value = p_min_value
        self.max_value = p_max_value

        self.multiple = p_multiple

        self.show_markers = False

        self.on_change = p_on_change

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def set_text(self, p_text):
        self.text = p_text

    def get_value(self):
        return self.value

    def set_value(self, p_value):
        if (self.value != p_value):
            self.value = p_value

            if (self.on_change):
                for f in self.on_change:
                    f()

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):

        # How far has the user moved the slider?
        percent = int( ((1.0 * self.value) / (1.0 * self.max_value)) * self.width)

        draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.background)
        draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], percent, self.height, self.shade)
        draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.border_color, 2)

        if (len(self.text) > 0):
            gui_text_renderer.render_with_wrap(self.text, (self.coords[0] + p_offset[0]) + (self.width / 2), (self.coords[1] + p_offset[1]), (255, 255, 255), align = "center")

        if (self.show_markers):
            for i in range(self.min_value, self.max_value + self.multiple, self.multiple):
                bar_width = (self.width / ((self.max_value - self.min_value + self.multiple) / self.multiple))
                x_offset = ((i - self.min_value) / self.multiple) * bar_width

                draw_rect(p_offset[0] + self.coords[0] + x_offset, p_offset[1] + self.coords[1], 1, self.height, (255, 255, 255))
                gui_text_renderer.render_with_wrap("%d" % i, p_offset[0] + self.coords[0] + x_offset + (bar_width / 2), p_offset[1] + self.coords[1] - 25, (255, 255, 255), align = "center")

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        self.active = 0

        # Let's see if we're hovering on the slider...
        pos_mouse = pygame.mouse.get_pos()

        result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height) )
        if (result and (not masked)):

            # Draw a border to highlight the fact that there's a mouseover
            #draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, (255, 255, 255), 1)

            self.active = 1

            if (pygame.mouse.get_pressed()[0]):
                offset_x = pos_mouse[0] - (self.coords[0] + p_offset[0])

                new_value = int( ((1.0 * offset_x) / (1.0 * self.width)) * self.max_value)

                # Round to the nearest multiple (perhaps the slider can only have values of 0, 5, 10, 15, and 20).
                # Add the multiple definition, then divide and multiply to emulate rounding.
                self.set_value( ( (new_value + self.multiple) / self.multiple) * self.multiple )

            return True

        else:
            self.active = 0

            return False

class Scrollbar(Element):
    def __init__(self, p_width, p_height, p_coords=(0,0), p_min_value=0, p_max_value=10, p_multiple=1, p_on_change=None, p_listener=None, background = None, background_active = None, border_color = None, border_color_active = None, text_color = None, text_color_active = None, has_rounded_corners = False):
        Element.__init__(self, p_coords,
                         background = background,
                         background_active = background_active,
                         border_color = border_color,
                         border_color_active = border_color_active,
                         text_color = text_color,
                         text_color_active = text_color_active,
                         has_rounded_corners = False)
        self.element_type = "Scrollbar"

        self.value = p_min_value

        self.width = p_width
        self.height = p_height

        self.scrollbar_color = (200, 200, 200)

        self.min_value = p_min_value
        self.max_value = p_max_value

        self.multiple = p_multiple

        self.on_change = p_on_change

        self.listener = p_listener

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_value(self):
        return self.value

    def set_value(self, p_value):
        if (self.value != p_value):
            self.value = p_value

            if (self.on_change):
                for f in self.on_change:
                    f()

    def step_down(self):

        if (self.value < self.max_value):
            self.value += self.multiple

            if (self.value > self.max_value):
                self.value = self.max_value

            if (self.on_change):
                for f in self.on_change:
                    f()

    def step_up(self):

        if (self.value > self.min_value):
            self.value -= self.multiple

            if (self.value < self.min_value):
                self.value = self.min_value

            if (self.on_change):
                for f in self.on_change:
                    f()

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):

        # I don't want the scroll smaller than 12 pixels tall
        scrollbar_size = self.height

        if (self.max_value - self.min_value > 0):
            try:
                scrollbar_size = max(36, int(self.height / ( (self.max_value - self.min_value) / self.multiple)))
            except:
                scrollbar_size = 36

            draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.background)
            draw_rect(self.coords[0] + p_offset[0], max(self.coords[1] + p_offset[1], self.coords[1] + p_offset[1] + 12 + ( float(self.get_value() / float(self.max_value)) * (self.height - 12)) - scrollbar_size), self.width, scrollbar_size, self.scrollbar_color)
            draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.border_color, 2)

        else:
            draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.background)
            draw_rect(self.coords[0] + p_offset[0], max(self.coords[1] + p_offset[1], self.coords[1] + p_offset[1] + 12 + ( 0 * (self.height - 12)) - scrollbar_size), self.width, scrollbar_size, self.scrollbar_color)
            draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.border_color, 2)

        if (self.active):

            # Draw a border to highlight the fact that there's a mouseover
            draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, (0.5, 0.5, 0.5), 1)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        self.active = 0

        if (self.listener):
            self.max_value = self.listener()

        # Let's see if we're hovering on the slider...
        pos_mouse = pygame.mouse.get_pos()

        if (self.has_mouse(p_offset) and (not masked)):

            self.active = 1

            if (pygame.mouse.get_pressed()[0]):

                # I don't want the scroll smaller than 12 pixels tall
                scrollbar_size = max(12, int(self.height / ( (self.max_value - self.min_value) / self.multiple)))

                offset_y = pos_mouse[1] - (self.coords[1] + p_offset[1])
                new_value = int( (float(offset_y) / float(self.height)) * (self.max_value - self.min_value))

                if (offset_y < 12):
                    new_value = 0
                elif (self.height - offset_y < 12):
                    new_value = self.max_value

                # Round to the nearest multiple (perhaps the slider can only have values of 0, 5, 10, 15, and 20).
                # Add the multiple definition, then divide and multiply to emulate rounding.
                #self.set_value( ( (new_value + self.multiple) / self.multiple) * self.multiple )
                self.set_value(new_value)

            return True

        return False

class Checkbox(Element):
    def __init__(self, p_width, p_height, p_coords=(0,0), p_on_click=None):
        Element.__init__(self, p_coords)
        self.element_type = "Checkbox"

        self.checked = False

        self.coords = p_coords

        self.width = p_width
        self.height = p_height

        self.on_click = p_on_click

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def hide(self):
        self.visible = False

        if (self.child):
            self.child.hide()

    def check(self):
        self.checked = True

    def uncheck(self):
        self.checked = False

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):
        draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), (0, 0, 0))
        draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), (255, 255, 255), 2)

        if (self.active):

            # Draw a border to highlight the fact that there's a mouseover
            draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, (255, 255, 0, 0.5), 1)

        if (self.checked):

            draw_rect(p_offset[0] + self.coords[0] + 2, p_offset[1] + self.coords[1] + 2, self.get_width() - 4, self.get_height() - 4, (255, 0, 0))

            #draw_line(p_offset[0] + self.coords[0] + 1, p_offset[1] + self.coords[1] + 1, p_offset[0] + self.coords[0] + self.get_width() - 1, p_offset[1] + self.coords[1] + self.get_height() - 1, (255, 255, 255), 2)
            #draw_line(p_offset[0] + self.coords[0] + self.get_width() - 1, p_offset[1] + self.coords[1] + 1, p_offset[0] + self.coords[0] + 1, p_offset[1] + self.coords[1] + self.get_height() - 1, (255, 255, 255), 2)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        self.active = 0

        pos_mouse = pygame.mouse.get_pos()

        result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height) )
        if (result and (not masked)):

            if (mouse["clicked"]):
                self.checked = (not self.checked)

                if (self.on_click):
                    for f in self.on_click:
                        f()

            self.active = 1

            return True

        else:
            return False

class Button(Element):
    def __init__(self, p_text="", p_width=0, p_height=0, p_coords=(0,0), p_on_click=None, p_on_mouseover=None, p_on_mouseout=None, background=None, background_active=None, border_color=None, border_color_active=None, text_color=None, text_color_active=None, image=None, image_active=None, has_rounded_corners = True):
        Element.__init__(self, p_coords,
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               border_color_active = border_color_active,
                               text_color = text_color,
                               text_color_active = text_color_active,
                               has_rounded_corners = has_rounded_corners)

        self.element_type = "Button"

        self.text = p_text
        self.value = ""

        self.width = p_width
        self.height = p_height

        if (not self.text_color_active):
            self.text_color_active = self.text_color

        self.image = image
        self.image_active = image_active

        if (self.image):
            self.width = self.image.width
            self.height = self.image.height

        self.on_click = p_on_click
        self.on_mouseover = p_on_mouseover
        self.on_mouseout = p_on_mouseout

        self.onclick_events = []
        self.onmouseover_events = []

        self.moused_over = 0

        self.child = None

        self.params = {}

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text

    def add_child(self, child):
        self.child = child

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def pad(self, p_rect=(0,0,0,0)):
        self.padded_rects.append(p_rect)

        if (p_rect == None):
            self.padded_rects = []

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def hide(self):
        self.visible = False

        if (self.child):
            self.child.hide()

    def set_value(self, p_value):
        self.value = p_value

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):

        self.render_background(gui_text_renderer, p_offset, sprites)

        if (self.active):
            # Draw a border to highlight the fact that there's a mouseover
            #if (self.background_active):
            #    draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), self.background_active)

            if (self.image_active):
                self.image_active.draw(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], window_controller = window_controller)
            elif (self.image):
                self.image.draw(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], window_controller = window_controller)

            #if (self.border_color_active):
            #    draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, self.border_color_active, 1)

            gui_text_renderer.render_with_wrap(self.text, p_offset[0] + self.coords[0] + (self.width / 2), p_offset[1] + self.coords[1], self.text_color_active, self.width - 2, align = "center")

        else:
            #if (self.background):
            #    draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), self.background)

            if (self.image):
                self.image.draw(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], window_controller = window_controller)

            #if (self.border_color):
            #    draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), self.border_color, 1)

            gui_text_renderer.render_with_wrap(self.text, p_offset[0] + self.coords[0] + (self.width / 2), p_offset[1] + self.coords[1], self.text_color, self.width - 2, align = "center")

        if (self.child):
            if (self.child.is_visible()):
                self.child.draw(where, gui_text_renderer, (0, 0), window_controller = window_controller)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        self.active = False

        pos_mouse = pygame.mouse.get_pos()
        intersects_button = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height) )

        if ( (self.has_mouse(p_offset)) and (not masked) ):

            # See if we need to do anything on the mouseover
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

            if (intersects_button):
                self.active = True

                if (mouse["clicked"]):

                    #if (self.on_click):
                    #    for f in self.on_click:
                    #        f()

                    #for f in self.onclick_functions:
                    #    f()
                    for e in self.onclick_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": self.params
                        })

            if (self.child):
                self.child.show()#visible = 1#show(gui_text_renderer)
                self.child.set_coords(self.coords[0] + p_offset[0] + self.get_width(), self.coords[1] + p_offset[1])

                if (self.child.coords[0] + self.child.get_width() > 640):# or intersect_any(self.child.get_rect(), self.blacklist)):
                    self.child.set_coords(self.coords[0] + p_offset[0] - self.child.get_width(), self.child.coords[1])

                if (self.child.coords[1] + self.child.get_height() > 480):
                    self.child.set_coords(self.child.coords[0], self.coords[1] + p_offset[1] - self.child.get_height() + self.get_height())

                self.child.process(gui_text_renderer, (0, 0), masked, system_input, mouse)

            return True # We tell the GUI handler not to process any lower objects

        else:
            if (self.moused_over == 1):
                if (self.on_mouseout):
                    for f in self.on_mouseout:
                        f()

            if (self.child):
                self.child.hide()

            self.moused_over = 0

            return False # The GUI handler is able to handle a lower object because it didn't handle this one

class Capsule(Element):
    def __init__(self, h, coords, background = None, background_active = None, border_color = None, border_color_active = None, text_color = None, text_color_active = None, option_tuples = [], gui_text_renderer = None):

        Element.__init__(self, coords,
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               border_color_active = border_color_active,
                               text_color = text_color,
                               text_color_active = text_color_active)

        self.option_tuples = option_tuples

        self.padding = 5
        self.margin = 15

        self.width = self.calculate_width(gui_text_renderer)
        self.height = h

        self.current_option = 0

    def calculate_width(self, gui_text_renderer):

        total_width = 0

        for (text, onclick) in self.option_tuples:

            w = gui_text_renderer.size(text)
            total_width += w + (2 * self.margin)

        return total_width + (self.padding * 2)

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.width, self.height)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):

        x = p_offset[0] + self.coords[0] + self.padding
        y = p_offset[1] + self.coords[1]

        index = 0

        for (text, onclick) in self.option_tuples:

            w = gui_text_renderer.size(text)

            (mx, my) = pygame.mouse.get_pos()
            r1 = (mx, my, 1, 1)
            r2 = (x, y, w, self.height)

            if (intersect(r1, r2) and (not masked) and (mouse["clicked"])):
                self.current_option = index

                # Execute onclick event
                if (self.option_tuples[index][1]):
                    self.option_tuples[index][1]()

                return True # Tell the GUI handler not to process any objects behind this one

            x += (w + self.margin)
            index += 1

        return False # We can handle objects behind this one still

    def draw(self, where, gui_text_renderer, p_offset = (0, 0), sprites = None, window_controller = None):

        self.render_background(gui_text_renderer, p_offset, sprites)

        x = self.padding
        first = True

        index = 0

        for (text, onclick) in self.option_tuples:

            if (index == self.current_option):
                gui_text_renderer.render_with_wrap(text, x + p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.text_color_active)

            else:
                gui_text_renderer.render_with_wrap(text, x + p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.text_color)

            w = gui_text_renderer.size(text)

            x += (w + self.margin)

            if (first):
                draw_rect(p_offset[0] + self.coords[0] + x, p_offset[1] + self.coords[1], 1, self.height, self.border_color)
                x += self.margin

                first = False

            index += 1


class Text_Box(Element):
    def __init__(self, p_width, p_height, p_coords=(0,0), p_rows=1, background=(0, 0, 0), background_active=(50, 50, 50), border_color=(200, 200, 200), border_color_active=(50, 50, 200), text_color=(255, 255, 255), text_color_active=(255, 255, 221), has_rounded_corners = False):
        Element.__init__(self, p_coords,
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               border_color_active = border_color_active,
                               text_color = text_color,
                               text_color_active = text_color_active,
                               has_rounded_corners = has_rounded_corners)
        self.element_type = "Text_Box"

        self.text = ""
        self.text_visible = []
        self.rows = []

        self.editing = False

        self.center = False

        self.bounds = []
        self.row_bounds = [0, p_rows]

        self.width = p_width
        self.height = p_height

        self.num_rows = p_rows # Number of rows to display on the screen
        self.total_rows = 0 # Total number of rows of text
        self.current_row = 0

        self.scroll_point = 0

        self.blinking = False
        self.blink_wait = 0
        self.blink_wait_delay = 15

        for i in range(0, self.num_rows):
            self.bounds.append([0, 0])
            self.text_visible.append("")

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

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return (self.height * self.num_rows)

    def get_visible_height(self):
        return (self.height * self.num_rows)

    def get_text(self):
        return self.text

    def set_text(self, p_text, gui_text_renderer):
        for i in range(0, self.num_rows):
            self.text_visible[i] = ""

        self.text = p_text

        self.rows = self.compute_rows(gui_text_renderer)

        self.move_cursor("end", gui_text_renderer)

    def scroll_up(self, gui_text_renderer):
        if (self.row_bounds[0] > 0):
            self.row_bounds[0] -= 1

            self.compute_rows(gui_text_renderer)

    def scroll_down(self, gui_text_renderer):
        if (self.row_bounds[0] + self.num_rows <= self.get_row_count(gui_text_renderer)):
            self.row_bounds[0] += 1

            self.compute_rows(gui_text_renderer)

    def scroll_to(self, row):
        self.scroll_point = row

        if (self.scroll_point < 0):
            self.scroll_point = 0

        if (self.scroll_point + (self.num_rows) >= len(self.rows)):
            self.scroll_point = max(0, len(self.rows) - self.num_rows)

        if (self.setter):
            self.setter(self.scroll_point)

    def scroll_to2(self, p_row, gui_text_renderer):
        self.row_bounds[0] = p_row

        if (self.row_bounds[0] < 0):
            self.row_bounds[0] = 0

        elif (self.row_bounds[0] + self.num_rows >= self.total_rows):
            self.row_bounds[0] = self.total_rows - 1 - self.num_rows

        #self.compute_rows(gui_text_renderer)

    def get_scroll_max(self):
        return ( max(0, len(self.rows) - (self.num_rows - 1)) )

    def compute_rows(self, gui_text_renderer):
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

            elif (gui_text_renderer.size(temp_row) + gui_text_renderer.size(word + " ") <= self.width - (self.padding * 2)):
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

    def move_cursor(self, p_dx, gui_text_renderer):
        if (p_dx == "end"):
            self.cursor_position = len(self.text)
        elif (p_dx == "home"):
            self.cursor_position = 0
            self.current_row = 0
            self.compute_rows(gui_text_renderer)
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
                    if (gui_text_renderer.size(sub_str(self.text, i, self.bounds[0][1])) <= self.width - (self.padding * 2)):
                        self.bounds[0][0] = i
                    else:
                        break

                    i -= 1

                self.text_visible[0] = sub_str(self.text, self.bounds[0][0], self.bounds[0][1])

            if (self.cursor_position < self.bounds[self.current_row][0]):
                self.bounds[0][0] = self.cursor_position

            i = self.bounds[0][0] + 1

            while (i <= len(self.text)):
                if (gui_text_renderer.size(sub_str(self.text, self.bounds[0][0], i)) <= self.width):
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
                self.x_offset = 1 + self.coords[0] + gui_text_renderer.size(sub_str(self.rows[self.current_row][1], 0, self.cursor_position - self.rows[self.current_row][0]))
            else:
                self.x_offset = 1 + self.coords[0]

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):

        self.blink_wait += 1

        if (self.blink_wait >= self.blink_wait_delay):
            self.blink_wait = 0

            self.blinking = (not self.blinking)


        if (self.editing):
            self.current_background = self.background_active
            self.current_border_color = self.border_color_active

        else:
            self.current_background = self.background
            self.current_border_color = self.border_color

        # frame it
        #draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), self.border_color, 1)

        self.render_background(gui_text_renderer, p_offset, sprites)

        # Handle drawing for single-line box
        if (self.num_rows == 1):
            gui_text_renderer.render_with_wrap(self.text_visible[0], p_offset[0] + self.coords[0] + self.padding, p_offset[1] + self.coords[1], self.text_color)

        # Handle drawing for multi-line box
        else:
            for i in range(self.scroll_point, self.scroll_point + self.num_rows):
                if (i < len(self.rows)):
                    if (self.center):
                        gui_text_renderer.render_with_wrap(self.rows[i][1], p_offset[0] + self.coords[0] + (available_width / 2), p_offset[1] + self.coords[1] + ( (i - self.scroll_point) * self.height), self.text_color, align = "center")
                    else:
                        gui_text_renderer.render_with_wrap(self.rows[i][1], p_offset[0] + self.coords[0] + self.padding, p_offset[1] + self.coords[1] + ( (i - self.scroll_point) * self.height), self.text_color)

        # Highlight the frame on mouseover to say "hey!  click me if you want to edit me!"
        #if (self.active):
        #    draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height(), (255, 0, 0), 1)

        # If it's active, then display a cursor
        if (self.editing == 1):

            # First, I want to draw a cursor so we know where we are editing at
            if (self.num_rows == 1):
                self.x_offset = p_offset[0] + self.coords[0] + self.padding + gui_text_renderer.size(self.text[self.bounds[0][0] : self.cursor_position])

                if (self.blinking):
                    draw_rect(self.x_offset, p_offset[1] + self.coords[1], 1, self.height, (37, 135, 255))

            else:

                try:
                    self.x_offset = p_offset[0] + self.coords[0] + self.padding + gui_text_renderer.size(self.text[self.bounds[self.current_row][1] : self.cursor_position])
                except:
                    pass

                try:
                    self.x_offset = p_offset[0] + self.coords[0] + self.padding + gui_text_renderer.size(self.text_visible[self.current_row - self.scroll_point][0 : self.cursor_offset])
                except:
                    self.x_offset = self.padding
                #print self.text[self.bounds[self.current_row][1] : self.cursor_position]

                if (self.x_offset >= 0):
                    if (self.current_row >= self.scroll_point and self.current_row < (self.scroll_point + self.num_rows)):

                        if (self.blinking):
                            draw_rect(self.x_offset, p_offset[1] + self.coords[1] + (self.current_row - self.scroll_point) * self.height, 1, self.height, (37, 135, 255))

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
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

            # If the mouse intersects with the text box and no other GUI element is atop it, then make it active
            result = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height()) )
            if (result):
                self.editing = 1

                # Now let's figure out where they clicked.  We begin by checking for row of clicking
                row_clicked = self.scroll_point + (pos_mouse[1] - (p_offset[1] + self.coords[1])) / self.height # self.height designates the height of one row

                # Make sure that row exists
                if (row_clicked >= len(self.rows)):
                    row_clicked = len(self.rows) - 1

                # We have the row; now let's use the mouseX offset data to find out which character
                # they clicked around...
                mouse_x_offset = pos_mouse[0] - (p_offset[0] + self.coords[0])

                aggregate_width = 0
                placed_cursor = False

                if (len(self.rows) > 0):
                    for i in range(0, len(self.rows[row_clicked][1])):
                        aggregate_width += gui_text_renderer.size("%s" % self.rows[row_clicked][1][i])

                        if (aggregate_width > mouse_x_offset):
                            new_cursor_position = self.rows[row_clicked][0] + i
                            self.cursor_offset = i

                            self.move_cursor(new_cursor_position - self.cursor_position, gui_text_renderer)

                            placed_cursor = True
                            break

                    # They probably clicked on a line that the text doesn't fully span
                    # so we'll put the cursor at the end of that line.
                    if (not placed_cursor):
                        new_cursor_position = self.rows[row_clicked][0] + len(self.rows[row_clicked][1])
                        self.cursor_offset = len(self.rows[row_clicked][1])

                        self.move_cursor(new_cursor_position - self.cursor_position, gui_text_renderer)

                else:
                    self.move_cursor("end", gui_text_renderer)

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
                self.rows = self.compute_rows(gui_text_renderer)
                self.move_cursor(len(keyboard_buffer), gui_text_renderer)

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
                    self.rows = self.compute_rows(gui_text_renderer)

                    # Move the cursor back one space
                    self.move_cursor(-1, gui_text_renderer)

            # Reset backspace wait if necessary
            if (not pygame.key.get_pressed()[K_BACKSPACE]):
                self.backspace_wait = 0

            # Decrease return_wait
            if (self.return_wait > 0):
                self.return_wait -= 1

            # See if the user pressed RETURN
            #if (pygame.key.get_pressed()[K_RETURN] and self.return_wait <= 1):
            #    self.text = insert_char(" \n ", self.text, self.cursor_position)
            #    self.move_cursor(1, gui_text_renderer)

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
                    self.move_cursor(-1, gui_text_renderer)

                    # If we're holding control, then move to the previous word
                    if (pygame.key.get_pressed()[K_LCTRL]):

                        i = self.cursor_position - 1
                        while (i > 0):
                            if (self.text[i] == " "):
                                self.move_cursor(i - (self.cursor_position - 1), gui_text_renderer)
                                break

                            i -= 1

                            if (i == 0):
                                self.move_cursor("home", gui_text_renderer)

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
                    self.move_cursor(1, gui_text_renderer)

                    if (pygame.key.get_pressed()[K_LCTRL]):

                        i = self.cursor_position
                        while (i < len(self.text)):
                            if (self.text[i] == " "):
                                self.move_cursor(i - (self.cursor_position - 1), gui_text_renderer)
                                break

                            i += 1

                            if (i == len(self.text)):
                                self.move_cursor("end", gui_text_renderer)

            if (not pygame.key.get_pressed()[K_RIGHT]):
                self.right_arrow_wait = 0

            ###

            if (pygame.key.get_pressed()[K_HOME]):
                self.move_cursor("home", gui_text_renderer)

            if (pygame.key.get_pressed()[K_END]):
                self.move_cursor("end", gui_text_renderer)

        # Is the mouse over this element?
        r = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height()) )
        if (r and (not masked)):
            self.active = 1

            return True # If so, then tell the GUI Handler not to allow the mouse to touch lower elements

        return False # If not, the mouse has the freedom to touch lower elements

class Rectangle(Element):
    def __init__(self, p_width, p_height, p_color, p_coords=(0,0), p_framed=False, p_frame_color=None, has_rounded_corners = False):
        Element.__init__(self, p_coords, has_rounded_corners = has_rounded_corners)

        self.element_type = "Rectangle"

        self.coords = p_coords

        self.width = p_width
        self.height = p_height

        self.color = p_color

        self.framed = p_framed
        self.frame_color = p_frame_color

    def get_rect(self):
        return (0, 0, 0, 0)

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):
        if (self.color):
            draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.color)

        if (self.framed):
            draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height, self.frame_color, 2)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        pos_mouse = pygame.mouse.get_pos()

        r = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height) )
        if (r):
            return True

        return False

class Hidden(Element):
    def __init__(self, p_value=None):
        Element.__init__(self, (0, 0))

        self.element_type = "Hidden"

        self.value = p_value

    def set_value(self, p_value=None):
        self.value = p_value

    def get_value(self):
        return self.value

    def get_rect(self):
        return (0, 0, 0, 0)

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):
        return

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        return False # Hidden element would never mask another element

class Listener(Element):
    def __init__(self, p_source, p_callback):
        Element.__init__(self, (0, 0))

        self.element_type = "Listener"

        self.source = p_source
        self.callback = p_callback

    def get_rect(self):
        return (0, 0, 0, 0)

    def draw(self, where, gui_text_renderer, p_offset = (0, 0), sprites = None, window_controller = None):
        return

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):
        if (self.source and self.callback):
            self.callback(self.source())

        return False

class Label(Element):
    def __init__(self, p_text, p_coords, styles=[], background=None, text_color=(0, 0, 0), text_color_active=(0, 0, 0), style="", align = None):
        Element.__init__(self, p_coords)
        self.element_type = "Label"
        self.text = p_text

        self.background = background
        self.border_color = None
        self.border_size = 1
        self.color = text_color
        self.color_active = text_color_active
        self.style = style
        self.max_width = -1

        self.current_width = 0

        self.align = align

        for each in styles:

            if (each[0] == "background"):
                self.background = each[1]

            elif (each[0] == "border"):
                self.border = each[1]

            elif (each[0] == "border_color"):
                self.border_color = each[1]

            elif (each[0] == "border_size"):
                self.border_size = int(each[1])

            elif (each[0] == "color"):
                self.color = each[1]

            elif (each[0] == "style"):
                self.style = each[1]

    def get_rect(self):
        return (0, 0, 0, 0)

    def set_max_width(self, p_max_width):
        self.max_width = p_max_width

    def set_color(self, p_color):
        self.color = p_color

    def set_text(self, p_text, gui_text_renderer):
        self.text = p_text
        self.current_width = gui_text_renderer.size(self.text)

    def get_text(self):
        return self.text

    def get_width(self):
        return 0

    def get_height(self):
        return 0

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):
        if (self.background != None):
            draw_rect(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], gui_text_renderer.size(self.text), 32, self.background)

        if (self.border_color != None):
            draw_rect_frame(self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], gui_text_renderer.size(self.text), 32, self.border_color, self.border_size)

        (x, y) = (
            p_offset[0] + self.coords[0],
            p_offset[1] + self.coords[1]
        )

        if (self.align == "center"):
            x -= int(self.current_width / 2)

        elif (self.align == "right"):
            x -= self.current_width

        color = self.color
        if (self.active):
            color = self.color_active

        gui_text_renderer.render_with_wrap(self.text, x, y, color, 1000 + self.max_width, self.style)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):

        (mx, my) = pygame.mouse.get_pos()

        r = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.current_width, 25)
        mr = (mx, my, 1, 1)

        self.active = False

        if ( (True or not masked) and (intersect(r, mr)) ):
            self.active = True

        return False
        pos_mouse = pygame.mouse.get_pos()

        r = intersect( (pos_mouse[0], pos_mouse[1], 1, 1), (self.coords[0], self.coords[1], gui_text_renderer.size(self.text), self.height) )
        if (r):
            return True

        return False

class Dialog(Element):

    def __init__(self, p_x, p_y, p_width, p_height, background = None, background_active = None, border_color = None, process_function=None, has_rounded_corners = True, is_floating = False):

        Element.__init__(self, (p_x, p_y),
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               has_rounded_corners = has_rounded_corners)

        self.element_type = "Dialog"

        self.width = p_width
        self.height = p_height

        # Give the dialog its own in-house GUI manager
        self.gui_manager = GUI_Manager()

        self.elements = []
        self.actions = {}

        self.process_function = process_function
        self.process_callback = None

        self.is_floating = is_floating

    def hide(self):
        self.visible = False

        if (self.child):
            self.child.hide()

        for name in self.gui_manager.widgets:

            self.gui_manager.widgets[name].hide()


    def show(self):
        self.visible = True

        if (self.child):
            self.child.show()

        for name in self.gui_manager.widgets:

            self.gui_manager.widgets[name].show()

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def has_mouse(self, p_offset=(0, 0)):
        self_has_mouse = self.is_visible() and intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (self.coords[0], self.coords[1], self.get_width(), self.get_height()) )
        child_has_mouse = False

        if (self.child):
            child_has_mouse = self.child.is_visible() and self.child.has_mouse(p_offset)

        for (type, each) in self.elements:
            if (each.has_mouse(p_offset)):
                child_has_mouse = True

        return (self_has_mouse or child_has_mouse)

    def set_background(self, p_background):
        self.background = p_background

    def set_border(self, p_border):
        self.border_color = p_border

    def add_element(self, p_id, p_element):
        self.elements.append([p_id, p_element])


    # Something of a hacky redirect
    def get_widget_by_name(self, name):

        # Need to peek into the in-house GUI manager
        return self.gui_manager.get_widget_by_name(name)


    def get_element(self, p_id):
        for (id, e) in self.elements:
            if (id == p_id):
                return e

        return None


    def get_elements_by_type(self, element_type):

        results = []

        for (id, e) in self.elements:
            if (e.element_type == element_type or element_type == "*"):
                results.append(e)

        return results

    def get_elements_with_aliases_by_type(self, element_type):

        results = []

        for (alias, e) in self.elements:

            if (e.element_type == element_type or element_type == "*"):
                results.append( (alias, e) )

        return results

    def define_action(self, p_id, p_action):
        self.actions[p_id] = p_action

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):

        if (self.height > 0):
            self.render_background(gui_text_renderer, p_offset, sprites)

        if (self.process_function):
            data = self.process_function()

            if (self.process_callback):
                self.process_callback(data)

        self.gui_manager.draw_all(gui_text_renderer = gui_text_renderer, p_offset = (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1]), window_controller = window_controller)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):

        #if (not masked):
        #    if (intersect( (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):
        #        if (pygame.mouse.get_pressed()[1]):
        #           self.coords = (pygame.mouse.get_pos()[0] - 24, pygame.mouse.get_pos()[1] - 24)

        masked |= self.gui_manager.process(masked = masked, gui_text_renderer = gui_text_renderer, p_offset = (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1]), system_input = system_input, mouse = mouse)

        self.pending_events.extend( self.gui_manager.fetch_events() )

        if (masked or intersect( (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, self.height), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):
            return True

        elif (self.is_floating):
            self.hide()

        return False

##################################################

# ** I think this class is obselete...
"""
class Status_Bar:
    def __init__(self):
        self.surface = None
        self.width = 0

        self.gamma_value = 0
        self.fade_wait = 0
        self.text = ""

    def setup(self, p_text, gui_text_renderer):
        self.width = gui_text_renderer.size(p_text) + 10
        self.surface = pygame.Surface((self.width, 12)).convert()

        pygame.draw.rect(self.surface, (0, 0, 0), (0, 0, self.width, 12))
        pygame.draw.rect(self.surface, (255, 255, 255), (0, 0, self.width, 12), 2)

        gui_text_renderer.draw_text_to(self.surface, p_text, self.width / 2, 0, (255, 255, 255), "center")

        self.gamma_value = 0
        self.fade_wait = 250
        self.fade_top = 250

    def draw(self, where, p_x, p_y, style="", window_controller = None):
        if (self.fade_wait > 0):
            if (self.fade_top - self.fade_wait < 200 / 4):
                self.surface.set_alpha( (self.fade_top - self.fade_wait) * 4 )
            elif (self.fade_wait < 200 / 4):
                self.surface.set_alpha( self.fade_wait * 4 )

            if (style == "center"):
                where.blit(self.surface, (p_x - (self.width / 2), p_y), (0, 0, self.width, 12))
            else:
                where.blit(self.surface, (p_x, p_y), (0, 0, self.width, 12))

            self.fade_wait -= 1
"""


class Fader:
    def __init__(self, speed=0.02, hover=0):
        self.gamma_value = 0.0
        self.gamma_max = 0.65

        self.speed = speed

        self.hover_count = 0
        self.hover = hover

        if (self.hover == "instant"):
            self.gamma_value = self.gamma_max
            self.hover = "forever"

        self.finished = False

    def fade_in(self):
        self.gamma_value += 0.02

        self.finished = False

        if (self.gamma_value >= self.gamma_max):
            self.gamma_value = self.gamma_max

            self.hover_count += 1

            if (self.hover == "forever"):
                pass

            elif (self.hover_count >= self.hover):
                self.hover_count = 0

                self.finished = True

                return False

        return True

    def fade_out(self):
        self.gamma_value -= 0.02

        #self.finished = False

        if (self.gamma_value <= 0.0):
            self.gamma_value = 0.0

            return False

        return True

    def fade_all(self):
        self.gamma_value = 0.0

        self.finished = False

        return False

    def show_all(self):
        self.gamma_value = self.gamma_max

        self.finished = True

        return False

class Tooltip(Fader, Element):
    def __init__(self, text="", x=0, y=0, background=(50, 50, 50, 1.0), border_color=(255, 255, 255), text_color=(255, 255, 255), speed=0.02, hover=0, width="auto", minimum_height="auto", center_text=False, has_rounded_corners = False):
        Element.__init__(self, (x, y), has_rounded_corners = True)
        Fader.__init__(self, speed = speed, hover = hover)

        self.element_type = "Tooltip"

        self.text = text
        self.center_text = center_text

        self.x = x
        self.y = y

        self.width = width
        self.minimum_height = minimum_height

        self.background = background
        self.border_color = border_color
        self.text_color = text_color

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

    def set_text(self, text, gui_text_renderer = None):

        self.line_count = 1

        self.text = text.replace("<br>", "\n")
        self.text = text.replace("[br]", "\n")

        # If we don't automatically set the width of this tooltip,
        # then we'll need to split long lines automatically so that
        # they will fit into the specified with.
        if (self.width != "auto" and self.text.replace(" ", "") != ""):

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
                    this_word_width = gui_text_renderer.size(words[j] + " ")

                    # If we can still fit the word in, then add it as normal
                    if (current_line_width + this_word_width < (self.width - 10) ):

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

    def get_rect(self):
        return (self.x, self.y, self.width, self.get_height())

    def get_width(self, gui_text_renderer=None):
        if (not gui_text_renderer):
            if (self.width == "auto"):
                return 0
            else:
                return self.width

        lines = self.text.split("\n")

        width = 0
        for line in lines:
            w = gui_text_renderer.size(line)
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

    def draw(self, where, gui_text_renderer, p_offset=(0,0), sprites = None, window_controller = None):
        #if (self.background):
        #    self.background = (self.background[0], self.background[1], self.background[2], self.gamma_value)
        #if (self.border_color):
        #    self.border_color = (self.border_color[0], self.border_color[1], self.border_color[2], self.gamma_value)
        #if (self.text_color):
        #    self.text_color = (self.text_color[0], self.text_color[1], self.text_color[2], self.gamma_value)
        self.current_background = self.background
        self.current_border_color = self.border_color

        self.render_background(gui_text_renderer, p_offset, sprites)

        lines = self.text.split("\n")

        width = 0

        if (self.width == "auto"):
            for line in lines:
                w = gui_text_renderer.size(line)
                if (w > width):
                    width = w

            width += 10

        else:
            width = self.width

        height = (len(lines) * 20) + 10
        if (self.minimum_height != "auto"):
            height = max(self.minimum_height, height)

        #if (self.background):
        #    draw_rect(self.x + p_offset[0], self.y + p_offset[1], width, height, self.background)
        #if (self.border_color):
        #    draw_rect_frame(self.x + p_offset[0], self.y + p_offset[1], width, height, self.border_color, 1)

        if (not self.limit):
            for i in range(0, len(lines)):
                if (self.center_text):
                    gui_text_renderer.render_with_wrap(lines[i], self.x + p_offset[0] + 5 + ( (width - 10) / 2), self.y + p_offset[1] + 3 + (i * 20), self.text_color, align = "center")
                else:
                    gui_text_renderer.render_with_wrap(lines[i], self.x + p_offset[0] + 5, self.y + p_offset[1] + 3 + (i * 20), self.text_color)

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
                        gui_text_renderer.render_with_wrap(lines[i], self.x + p_offset[0] + 5 + ( (self.width - 10) / 2), self.y + p_offset[1] + 3 + (i * 20), self.text_color, align = "center")
                    else:
                        gui_text_renderer.render_with_wrap(lines[i], self.x + p_offset[0] + 5, self.y + p_offset[1] + 3 + (i * 20), self.text_color)

                # Otherwise... if the cursor is on this very line...
                # We will figure out how much of the line we want to draw.
                elif (self.cursor > (previous_length - len(lines[i]))):
                    string = sub_str(self.text, previous_length - len(lines[i]), self.cursor).replace("\n", "")

                    if (self.center_text):
                        gui_text_renderer.render_with_wrap(string, self.x + p_offset[0] + 5 + ( (self.width - 10) / 2), self.y + p_offset[1] + 3 + (i * 20), self.text_color, align = "center")
                    else:
                        gui_text_renderer.render_with_wrap(string, self.x + p_offset[0] + 5, self.y + p_offset[1] + 3 + (i * 20), self.text_color)

class Dropdown(Element):

    def __init__(self, x, y, w, h, numrows, background = None, background_active = None, border_color = None, border_color_active = None, text_color = None, text_color_active = None):

        Element.__init__(self, (x, y),
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               border_color_active = border_color_active,
                               text_color = text_color,
                               text_color_active = text_color_active,
                               has_rounded_corners = False)
        self.element_type = "Dropdown"

        self.width = w
        self.height = h

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

        self.coords = (x, y)

        #self.on_change = p_on_change

        self.beforechange_events = []
        self.onchange_events = []


        # Scroll through the list when necessary
        self.scrollbar = Scrollbar(
            int(self.height / 2),
            self.height * self.numrows,
            (0, 0),
            0, 0, 1,
            background = background,
            background_active = background_active,
            border_color = border_color,
            border_color_active = border_color_active,
            text_color = text_color,
            text_color_active = text_color_active,
            has_rounded_corners = False
        )

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_value(self):

        if (self.selection):
            return self.selection["value"]

        else:
            return ""

    def select(self, title):

        # Check all row data to find the first value match...
        for r in self.rows:

            if (r["title"] == title):

                # Raise any beforechange event...
                for e in self.beforechange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                self.selection = r

                # Raise any onchange event...
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                return True

        # Well, if we're still here, then we couldn't find it.
        return False

    def select_by_value(self, value):

        # Check all row data to find the first value match...
        for r in self.rows:

            if (r["value"] == value):

                # Raise any beforechange event...
                for e in self.beforechange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                self.selection = r

                # Raise any onchange event...
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                return True

        # Well, if we're still here, then we couldn't find it.
        return False

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

    def has_mouse(self, p_offset=(0, 0)):

        if (not self.is_visible()):
            return False

        self_has_mouse = intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height()) )

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
        self.show_dropdown = False
        self.selection = None

    def add(self, title, value):

        self.rows.append({
            "title": title,
            "value": value
        })

        # Will we need a scrollbar?
        if (len(self.rows) > self.numrows):
            self.scrollbar.max_value = len(self.rows) - self.numrows


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

    def draw(self, where, gui_text_renderer, p_offset = (0, 0), sprites = None, window_controller = None):

        # First, draw the active selection and the dropdown arrow
        if (self.active):

            draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, self.background_active)
            draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, self.border_color_active, 2)

            # Here is the dropdown arrow...
            draw_rect(p_offset[0] + self.coords[0] + self.width - self.height, p_offset[1] + self.coords[1], self.height, self.height, self.background) # arrow background never changes...
            draw_rect_frame(p_offset[0] + self.coords[0] + self.width - self.height, p_offset[1] + self.coords[1], self.height, self.height, self.border_color_active, 2)

            padding = 8
            draw_triangle(p_offset[0] + self.coords[0] + self.width - self.height + padding, p_offset[1] + self.coords[1] + padding, self.height - (2 * padding), self.height - (2 * padding), self.text_color_active, None, DIR_DOWN)

            if (self.selection):

                padding = 2

                r = (p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1], self.width - (padding * 2) - self.height, self.height)

                window_controller.get_scissor_controller().push(r)

                gui_text_renderer.render_with_wrap(self.selection["title"], p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + padding, self.text_color_active)

                window_controller.get_scissor_controller().pop()

        else:

            draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, self.background)
            draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height, self.border_color, 2)

            # Here is the dropdown arrow...
            draw_rect_frame(p_offset[0] + self.coords[0] + self.width - self.height, p_offset[1] + self.coords[1], self.height, self.height, self.border_color, 2)

            padding = 8
            draw_triangle(p_offset[0] + self.coords[0] + self.width - self.height + padding, p_offset[1] + self.coords[1] + padding, self.height - (2 * padding), self.height - (2 * padding), self.text_color, None, DIR_DOWN)

            if (self.selection):

                padding = 2

                r = (p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1], self.width - (padding * 2) - self.height, self.height)

                window_controller.get_scissor_controller().push(r)

                gui_text_renderer.render_with_wrap(self.selection["title"], p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + padding, self.text_color)

                window_controller.get_scissor_controller().pop()


        # If necessary, render the dropdown selections
        if (self.show_dropdown):

            h = (self.height * self.numrows)

            # Draw a background region
            draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + self.height, self.width, h, self.background)
            draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + self.height, self.width, h, self.border_color, 2)

            # Render each option from the current offset...
            pos = self.offset

            if (pos + self.numrows >= len(self.rows)):
                pos = len(self.rows) - self.numrows

                if (pos < 0):
                    pos = 0

            padding = 2

            # Dropdown area available to render text to...
            r = (p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + self.height, self.width - (padding * 2), (self.numrows * self.height))

            mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

            # If the scrollbar is needed...
            if (len(self.rows) > self.numrows):
                r = offset_rect(r, w = -1 * int(self.height / 2))

            window_controller.get_scissor_controller().push(r)

            for y in range(pos, min(pos + self.numrows, len(self.rows))):

                lr = (p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + self.height + (y * self.height), self.width - (padding * 2), (self.height))

                if (intersect(mr, lr)):
                    window_controller.get_scissor_controller().pop()

                gui_text_renderer.render_with_wrap(self.rows[y]["title"], p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + self.height + ( (y - pos) * self.height ), self.text_color)

                if (intersect(mr, lr)):
                    window_controller.get_scissor_controller().push(r)

                # Trailing border
                #draw_rect(p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + self.height + ( (y - pos) * self.height ) + self.height - (padding / 2), (self.width - (2 * padding)), padding, self.border_color)

            window_controller.get_scissor_controller().pop()


            # Does the dropdown require the scrollbar?
            if (len(self.rows) > self.numrows):

                self.scrollbar.draw(None, gui_text_renderer, (p_offset[0] + self.coords[0] + self.width - int(self.height / 2), p_offset[1] + self.coords[1] + self.height), window_controller = window_controller)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):

        #if (intersect( (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, height), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):
        #    if (mouse["scrolled"] == "up"):
        #        self.scroll_to(self.bounds[0] - 1)
        #   elif (mouse["scrolled"] == "down"):
        #        self.scroll_to(self.bounds[0] + 1)

        if (not self.show_dropdown):

            h = self.height#min(self.entry_height * self.num_rows, self.entry_height * len(self.row_data))

            if (intersect( (self.coords[0] + p_offset[0], self.coords[1] + p_offset[1], self.width, h), (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1))):

                if (not masked):
                    self.active = True

                    if (mouse["clicked"]):
                        self.toggle_dropdown()

                return True

            else:
                if (not masked):
                    self.active = False

                return False

        else:

            mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

            # Entire area
            rAll = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height + (self.numrows * self.height))

            # Current selection area
            rSelection = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, self.height)

            # Entire dropdown area
            rDropdown = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + self.height, self.width, (self.numrows * self.height))

            # Dropdown area available to click
            rDropdownClickable = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + self.height, self.width, (self.numrows * self.height))

            # Scrollbar area
            rDropdownScrollbar = (p_offset[0] + self.coords[0] + self.width - (self.height / 2), p_offset[1] + self.coords[1] + self.height, 0, (self.numrows * self.height))


            # If the scrollbar is needed...
            if (len(self.rows) > self.numrows):

                rDropdownClickable = offset_rect(rDropdownClickable, w = -1 * int(self.height / 2))
                rDropdownScrollbar = offset_rect(rDropdownScrollbar, w = int(self.height / 2))


            # Active?
            self.active = False

            if (intersect(rAll, mr) and (not masked)):

                self.active = True

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


                # Hovering over current selection value?
                if (intersect(rSelection, mr)):

                    if (mouse["clicked"]):
                        self.show_dropdown = False

                # Hovering over a dropdown selection?
                elif (intersect(rDropdownClickable, mr)):

                    if (mouse["clicked"]):

                        y = self.offset + int( (mr[1] - rDropdownClickable[1]) / self.height )

                        if (y < len(self.rows)):

                            # Raise any beforechange event...
                            for e in self.beforechange_events:
                                self.pending_events.append({
                                    "event-info": e,
                                    "parent": None,
                                    "params": {"dropdown-value": self.get_value()}
                                })

                            # We have a new selection...
                            self.selection = self.rows[y]

                            # Check for onchange events
                            for e in self.onchange_events:
                                self.pending_events.append({
                                    "event-info": e,
                                    "parent": None,
                                    "params": {"dropdown-value": self.get_value()}
                                })

                        # Hide the dropdown now that we've made a selection...
                        self.show_dropdown = False

                # Hovering over scrollbar?
                elif (intersect(rDropdownScrollbar, mr)):

                    self.scrollbar.process(gui_text_renderer, (rDropdownScrollbar[0], rDropdownScrollbar[1]), masked, system_input, mouse)

                    # Synchronize with the scroll bar...
                    self.offset = self.scrollbar.get_value()


            if ( (not self.active) and (mouse["clicked"]) ):
                self.show_dropdown = False

            # In the end, does this element mask others below it?
            if (intersect(rAll, mr)):
                return True

            else:
                return False

class Listbox(Element):

    def __init__(self, x, y, w, h, numrows, background = None, background_active = None, border_color = None, border_color_active = None, text_color = None, text_color_active = None):

        Element.__init__(self, (x, y),
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               border_color_active = border_color_active,
                               text_color = text_color,
                               text_color_active = text_color_active,
                               has_rounded_corners = False)
        self.element_type = "Dropdown"

        self.width = w
        self.height = h

        # How many rows appear in the dropdown at a given time?
        self.numrows = numrows

        # Store the dropdown options
        self.rows = []

        # Active selection?
        self.selection = None

        # Store the scroll offset
        self.offset = 0

        self.coords = (x, y)

        #self.on_change = p_on_change

        self.beforeclick_events = []
        self.onclick_events = []
        self.onchange_events = []


        # Scroll through the list when necessary
        self.scrollbar = Scrollbar(
            int(self.height / 2),
            self.height * self.numrows,
            (0, 0),
            0, 0, 1,
            background = background,
            background_active = background_active,
            border_color = border_color,
            border_color_active = border_color_active,
            text_color = text_color,
            text_color_active = text_color_active,
            has_rounded_corners = False
        )

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def select(self, title):

        # Check all row data to find the first value match...
        for i in range(0, len(self.rows)):

            r = self.rows[i]

            if (r["title"] == title):

                # Raise any beforeclick event...
                for e in self.beforeclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                self.selection = r

                # Update offset
                self.offset = 0

                if (i >= self.numrows):
                    self.offset = (self.numrows - i)


                # Raise any onclick event...
                for e in self.onclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                # Raise any onchange event...
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                return True

        # Well, if we're still here, then we couldn't find it.
        return False

    def select_by_value(self, value):

        # Check all row data to find the first value match...
        for i in range(0, len(self.rows)):

            r = self.rows[i]

            if (r["value"] == value):

                # Raise any beforeclick event...
                for e in self.beforeclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

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
                for e in self.onclick_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                # Raise any onchange event...
                for e in self.onchange_events:
                    self.pending_events.append({
                        "event-info": e,
                        "parent": None,
                        "params": {"dropdown-value": self.get_value()}
                    })

                return True

        # Well, if we're still here, then we couldn't find it.
        return False

    def get_value(self):

        if (self.selection):
            return self.selection["value"]

        else:
            return ""

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

    def has_mouse(self, p_offset=(0, 0)):

        if (not self.is_visible()):
            return False

        self_has_mouse = intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height()) )

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
            "title": title,
            "value": value
        })

        # Will we need a scrollbar?
        if (len(self.rows) > self.numrows):
            self.scrollbar.max_value = len(self.rows) - self.numrows


        # Is this the default selection?
        if (self.selection == None):

            self.selection = {
                "title": title,
                "value": value
            }

    def draw(self, where, gui_text_renderer, p_offset = (0, 0), sprites = None, window_controller = None):

        # Render each visible item...
        h = (self.height * self.numrows)

        # Draw a background region
        draw_rect(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, h, self.background)
        draw_rect_frame(p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, h, self.border_color, 2)

        # Render each option from the current offset...
        pos = self.offset

        if (pos + self.numrows >= len(self.rows)):
            pos = len(self.rows) - self.numrows

            if (pos < 0):
                pos = 0

        padding = 5

        # Dropdown area available to render text to...
        r = (p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1], self.width - (padding * 2), (self.numrows * self.height))

        mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

        # If the scrollbar is needed...
        if (len(self.rows) > self.numrows):
            r = offset_rect(r, w = -1 * int(self.height / 2))

        window_controller.get_scissor_controller().push(r)

        for y in range(pos, min(pos + self.numrows, len(self.rows))):

            lr = (p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + ( (y - pos) * self.height) + padding, self.width - (padding * 2), (self.height - (padding * 2)))

            if (self.rows[y] == self.selection):
                draw_rect(lr[0], lr[1], lr[2], lr[3], self.background_active)

            if (intersect(mr, lr)):
                window_controller.get_scissor_controller().pop()
                gui_text_renderer.render_with_wrap(self.rows[y]["title"], p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + ( (y - pos) * self.height ), self.text_color_active)
                window_controller.get_scissor_controller().push(r)

            else:
                gui_text_renderer.render_with_wrap(self.rows[y]["title"], p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + ( (y - pos) * self.height ), self.text_color)

            # Trailing border
            #draw_rect(p_offset[0] + self.coords[0] + padding, p_offset[1] + self.coords[1] + self.height + ( (y - pos) * self.height ) + self.height - (padding / 2), (self.width - (2 * padding)), padding, self.border_color)

        window_controller.get_scissor_controller().pop()


        # Does the dropdown require the scrollbar?
        if (len(self.rows) > self.numrows):

            self.scrollbar.draw(None, gui_text_renderer, (p_offset[0] + self.coords[0] + self.width - int(self.height / 2), p_offset[1] + self.coords[1]), window_controller = window_controller)

    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):

        mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

        # Entire area
        rAll = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, (self.numrows * self.height))

        # Dropdown area available to click
        rDropdownClickable = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.width, (self.numrows * self.height))

        # Scrollbar area
        rDropdownScrollbar = (p_offset[0] + self.coords[0] + self.width - (self.height / 2), p_offset[1] + self.coords[1], 0, (self.numrows * self.height))


        # If the scrollbar is needed...
        if (len(self.rows) > self.numrows):

            rDropdownClickable = offset_rect(rDropdownClickable, w = -1 * int(self.height / 2))
            rDropdownScrollbar = offset_rect(rDropdownScrollbar, w = int(self.height / 2))


        # Active?
        self.active = False

        if (intersect(rAll, mr) and (not masked)):

            self.active = True

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
                    for e in self.beforeclick_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": {"dropdown-value": self.get_value()}
                        })

                    y = self.offset + int( (mr[1] - rDropdownClickable[1]) / self.height )

                    if (y < len(self.rows)):

                        # We have a new selection...
                        self.selection = self.rows[y]

                    # Hide the dropdown now that we've made a selection...
                    self.show_dropdown = False


                    # Check for onclick events
                    for e in self.onclick_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": {"dropdown-value": self.get_value()}
                        })

                    # Check for onchange events...
                    for e in self.onchange_events:
                        self.pending_events.append({
                            "event-info": e,
                            "parent": None,
                            "params": {"dropdown-value": self.get_value()}
                        })

            # Hovering over scrollbar?
            elif (intersect(rDropdownScrollbar, mr)):

                self.scrollbar.process(gui_text_renderer, (rDropdownScrollbar[0], rDropdownScrollbar[1]), masked, system_input, mouse)

                # Synchronize with the scroll bar...
                self.offset = self.scrollbar.get_value()


        if ( (not self.active) and (mouse["clicked"]) ):
            self.show_dropdown = False

        # In the end, does this element mask others below it?
        if (intersect(rAll, mr)):
            return True

        else:
            return False


class Treeview(Element):

    def __init__(self, x, y, w, h, row_height, background = None, background_active = None, border_color = None, border_color_active = None, text_color = None, text_color_active = None, root = True):

        Element.__init__(self, (x, y),
                               background = background,
                               background_active = background_active,
                               border_color = border_color,
                               border_color_active = border_color_active,
                               text_color = text_color,
                               text_color_active = text_color_active,
                               has_rounded_corners = False)
        self.element_type = "Treeview"

        self.root = root

        self.width = w  # Overall width
        self.height = h # Overall available height

        # Height per row?
        self.row_height = row_height

        # Is this the root of the tree?
        self.root = root

        # Store the dropdown options
        self.rows = []

        # Scrolling offset (row by row)
        self.row_offset = 0

        self.coords = (x, y)

        # Each branch can have a tooltip
        self.tooltip_width = 360
        self.tooltip = Tooltip(background = (25, 25, 25, 0.8), border_color = (225, 225, 225), text_color = (215, 215, 215), width = self.tooltip_width, hover = "instant")

        self.last_hovered = None
        self.hover_delay = None

        self.onclick_events = []
        self.onchange_events = []

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def get_rect(self):
        return (self.coords[0], self.coords[1], self.get_width(), self.get_height())

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def count(self):

        total = 0

        for r in self.rows:
            total += 1

            total += r["children"].count()

        return total

    def count_visible(self):

        total = 0

        for r in self.rows:
            total += 1

            if (r["toggled"]):
                total += r["children"].count_visible()

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

    def get_scroll_max(self):
        return len(self.rows) - self.numrows

    def has_mouse(self, p_offset=(0, 0)):

        log( 5/0 )

        if (not self.is_visible()):
            return False

        self_has_mouse = intersect( (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1), (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1], self.get_width(), self.get_height()) )

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

    def clear(self):
        self.rows = []
        self.toggled = False

    def add(self, elem, params, tooltip):

        #elem.x = 0
        #elem.y = 0

        #elem.width = (self.width - self.height)
        #elem.height = self.height

        self.rows.append({
            "element": elem,
            "params": params,

            "tooltip": tooltip,
            "tooltip-delay": TOOLTIP_DELAY,

            "toggled": False,
            "children": Treeview(0, 0, self.width, self.height, self.row_height, root = False,
                                 border_color = self.border_color,
                                 border_color_active = self.border_color_active,
                                 background = self.background,
                                 background_active = self.background_active,
                                 text_color = self.text_color,
                                 text_color_active = self.text_color_active)
        })

        return ( len(self.rows) - 1 )

    def add_to_branch(self, index, elem, params, tooltip):

        self.rows[index]["children"].add(elem, params, tooltip)
        self.rows[index]["toggled"] = True

        return ( len(self.rows[index]["children"].rows) - 1 )

    def draw(self, where, gui_text_renderer, p_offset = (0, 0), sprites = None, recursive = False, window_controller = None):

        (mx, my) = pygame.mouse.get_pos()
        mr = (mx, my, 1, 1)

        y = 0

        if (not recursive):
            y -= (self.row_offset * self.row_height)

        oy = y

        if (not recursive):
            window_controller.get_scissor_controller().push( (0, p_offset[1] + self.coords[1], SCREEN_WIDTH, self.height) )

        # Render each branch
        for branch in self.rows:

            rClick = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + y, self.width, self.row_height)

            # First, render the row itself.  Start with a background...
            r = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + y, self.width, self.row_height)
            padding = 0

            #r = offset_rect(r, -padding, -padding, padding * 2, padding * 2)

            color = branch["element"].background
            if (intersect(rClick, mr)):
                color = branch["element"].background_active

            if (color):
                draw_rect(rClick[0], rClick[1], rClick[2], rClick[3], color)



            # Render a +/- toggle
            if (branch["toggled"]):
                rButton = (rClick[0], rClick[1], self.row_height, self.row_height)

                color = self.border_color
                if (self.active):
                    color = self.border_color_active

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

                # Anchor lines
                ly = rButton[1] + rButton[3] + int(self.row_height / 2)

                for each in branch["children"].rows:

                    draw_rect(cx, ly - 1, int(rButton[2] / 2), 2, color)

                    ly += (1 + each["children"].count_visible()) * self.row_height
                    #ly += branch["children"].rows[each]["children"].count_visible() * self.row_height

            else:
                rButton = (rClick[0], rClick[1], self.row_height, self.row_height)

                color = self.border_color
                if (self.active):
                    color = self.border_color_active

                # Perimeter
                draw_rect_frame(rButton[0], rButton[1], rButton[2], rButton[3], color, 1)

                # + sign
                (cx, cy) = (
                    rButton[0] + int(rButton[2] / 2),
                    rButton[1] + int(rButton[3] / 2)
                )

                line_radius = (self.row_height / 2) - 6

                draw_rect(cx - line_radius, cy - 1, (line_radius * 2), 2, color)
                draw_rect(cx - 1, cy - line_radius, 2, (line_radius * 2), color)


            # Now render the element in this row
            branch["element"].draw(None, gui_text_renderer, (p_offset[0] + self.coords[0] + self.row_height, p_offset[1] + self.coords[1] + y), sprites, window_controller = window_controller)


            # Advance y cursor to the next row, irregardless...
            y += self.row_height


            # If this branch is toggled, we need to render any children as well...
            if (branch["toggled"]):

                # We'll end up advancing the y cursor by the amount of vertical space the child node requires...
                y += branch["children"].draw(None, gui_text_renderer, (rClick[0] + self.row_height, rClick[1] + self.row_height), sprites, recursive = True, window_controller = window_controller)

            # Otherwise, we do nothing...
            else:
                pass


        #if (self.hover_delay == 0):
        if (self.root == True):

            tooltip = self.get_tooltip()

            if (tooltip):

                (x, y) = (mx + 16, my + 16)

                if (x + self.tooltip_width > SCREEN_WIDTH):
                    x = mx - self.tooltip_width

                tooltip.draw(None, gui_text_renderer, (x, y), sprites, window_controller = window_controller)


        if (not recursive):
            window_controller.get_scissor_controller().pop()


        # Return the height we required for rendering this branch...
        return y


    def process(self, gui_text_renderer, p_offset = (0, 0), masked = False, system_input = {}, mouse = {}, parent = None):

        result = False

        y = 0

        if (parent == None):
            y -= (self.row_offset * self.row_height)

        mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)

        draw_rect(mr[0], mr[1], mr[2], mr[3], (0, 255, 0))

        hover_item = None

        # Process each branch
        for branch in self.rows:

            rClick = (p_offset[0] + self.coords[0], p_offset[1] + self.coords[1] + y, self.width, self.row_height)

            #draw_rect_frame(rClick[0], rClick[1], rClick[2], rClick[3], (0, 0, 255), 2)

            rButton = (rClick[0], rClick[1], self.row_height, self.row_height)

            # Check for mouse hover
            if ( (not masked) and (intersect(mr, rButton)) ):

                if (mouse["clicked"]):
                    branch["toggled"] = (not branch["toggled"])


            if ( (not masked) and (intersect(mr, rClick)) ):

                result = True # Has mouse
                hover_item = branch # Track


                if (parent == None):

                    # Check for mouse scrolling
                    if (mouse["scrolled"] == "down"):
                        self.row_offset += 1

                    elif (mouse["scrolled"] == "up"):
                        self.row_offset -= 1

                        if (self.row_offset < 0):
                            self.row_offset = 0


            # Right-click on the row?
            if ( (not masked) and (intersect(mr, rClick)) and (mouse["rightclicked"]) ):

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

            # Advance y cursor to the next row, irregardless...
            y += self.row_height


            # If this branch is toggled, we need to render any children as well...
            if (branch["toggled"]):

                # We'll end up advancing the y cursor by the amount of vertical space the child node requires...
                result |= branch["children"].process(gui_text_renderer, (rClick[0] + self.row_height, rClick[1] + self.row_height), masked, system_input, mouse, self)

                y += branch["children"].count_visible() * self.row_height

            # Otherwise, we do nothing...
            else:
                pass


        if (hover_item != self.last_hovered):

            self.last_hovered = hover_item
            self.hover_delay = 60

            self.tooltip.hide()

        elif (self.last_hovered != None):

            if (self.hover_delay > 0):
                self.hover_delay -= 1

            else:
                self.tooltip.set_text(self.last_hovered["tooltip"], gui_text_renderer)

                self.tooltip.x = 0
                self.tooltip.y = 0

                self.tooltip.show()

        return result
