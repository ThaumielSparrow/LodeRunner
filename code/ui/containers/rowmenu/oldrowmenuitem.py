class RowMenuItem:

    def __init__(self, widget):

        # Item can have an optional id
        self.id = None


        # Item may specify a parent id (for rendering purposes, like display = 'with-parent,' perhaps)
        self.parent_id = None

        # If another item chooses to display with this item, then that other item (the with-parent item)
        # becomes a "friend" of this item (sharing focus and blur events)
        self.friend_ids = []


        # The widget container within this RowMenuItem
        self.item = widget

        # I typically track visibility within the lowest level widgets (<label />, etc.).
        # For RowMenuItems, though, I'll permit this wrapper to also have a "visibility" setting,
        # separate from the standard "display" attribute of low-level widgets.
        self.visibility = "visible"

        # An item may be entirely hidden from view (no height, no rendering, nothing)
        # Primarily used for static dialogue panels, etc., to serve as a "hidden input" field
        # (i.e. key listener)
        self.hidden = False


        # An item might not be selectable by the user
        self.disabled = False

        # Perhaps the single item (within a group) has an individual border?
        self.individual_border = False

        # Shrinkwrap to rnder only necessary border width?
        self.shrinkwrap = False

        # Perhaps we'll render a glowing highlight behind the text of the active selection?
        self.glow = False

        # Occasionally we'll hard-code the height for a given item
        self.explicit_height = None


        # Sometimes a row menu item will have a tooltip (which is basically a simple GridMenuCell)
        self.tooltip = None


        # A RowMenuItem may have other special properties if they begin with a -
        self.additional_properties = {}


    def configure(self, options):

        if ( "id" in options ):
            self.id = options["id"]

        if ( "parent-id" in options ):
            self.parent_id = options["parent-id"]

        if ( "visibility" in options ):
            self.visibility = options["visibility"]

        if ( "hidden" in options ):
            self.hidden = options["hidden"]

        if ( "disabled" in options ):
            self.disabled = int( options["disabled"] )

        if ( "individual-border" in options ):
            self.individual_border = int( options["individual-border"] )

        if ( "shrinkwrap" in options ):
            self.shrinkwrap = int( options["shrinkwrap"] )

        if ( "glow" in options ):
            self.glow = int( options["glow"] )

        if ( "explicit-height" in options ):
            self.explicit_height = int( options["explicit-height"] )


        # Check for special additional properties
        for key in options:

            # Must start with a -
            if ( key.startswith("-") ):

                # Save it
                self.additional_properties[key] = options[key]


        #print "..."
        #print options
        #print self.additional_properties
        #print 5/0


        # For chaining
        return self


    # Get a special property
    def get_property(self, key):

        # Validate
        if (key in self.additional_properties):

            return self.additional_properties[key]

        else:

            return None


    def get_widget_container(self):

        return self.item


    # Event callbacks
    def while_awake(self):

        # Forward message
        self.get_widget().while_awake()


    def while_asleep(self):

        # Forward message
        self.get_widget().while_asleep()


    def on_blur(self):

        # Forward message
        self.get_widget().on_blur()


    def get_widget(self):

        return self.item


    # used in widget height calculations (e.g. overall RowMenu height)
    def get_box_height(self, text_renderer):

        # Hidden items have no height
        if (self.hidden):

            return 0

        elif (self.explicit_height != None):

            return (self.explicit_height)

        else:

            #print "Advance, check box height for %s" % self.item
            return (self.item.get_box_height(text_renderer))


    # Used to determine render region for backgrounds and the like
    def get_render_height(self, text_renderer):

        # Hidden items have no height
        if (self.hidden):

            return 0

        elif (self.explicit_height != None):

            return self.explicit_height

        else:

            return self.item.get_render_height(text_renderer)


    def get_min_x(self, text_renderer):

        return self.item.get_min_x(text_renderer)


    def add_tooltip(self):#, width, align, delay, lifespan, margin_x = 20, margin_y = 0):

        self.tooltip = RowMenuTooltip()#RowMenuItemTooltip(width, align, delay = delay, lifespan = lifespan, margin_x = margin_x, margin_y = margin_y)

        return self.tooltip
