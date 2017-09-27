from code.game.scripting.script import Script

from code.constants.common import ACHIEVEMENT_STATUS_ACTIVE, ACHIEVEMENT_STATUS_COMPLETE, ACHIEVEMENT_STATUS_FAILED

class Achievement:

    def __init__(self):

        # The name of the achievement (for scripting references, etc.)
        self.name = ""

        # The readable title of the achievement (for display)
        self.title = "--"

        # Readable description
        self.description = "--"


        # Current status of this achievement
        self.status = ACHIEVEMENT_STATUS_ACTIVE


        # An achievement can (should) load in one or more "hooks" (scripts)
        # that execute following certain hook events (e.g. collect gold, kill bad guy, etc.)
        # We'll hash these by the hook event type.
        self.hooks = {}


    # Load state (via XMLNode)
    def load_state(self, node):

        # Name
        if ( node.find_node_by_tag("name") ):

            # Read
            self.name = node.find_node_by_tag("name").innerText

        # Title
        if ( node.find_node_by_tag("title") ):

            # Read
            self.title = node.find_node_by_tag("title").innerText


        # Description
        if ( node.find_node_by_tag("description") ):

            # Read
            self.description = node.find_node_by_tag("description").innerText


        # Look for hooks
        ref_hooks = node.find_node_by_tag("hooks")

        # Validate
        if (ref_hooks):

            # Loop provided hooks
            for ref_hook in ref_hooks.get_nodes_by_tag("hook"):

                # Get references to hook name and script data
                (ref_name, ref_script) = (
                    ref_hook.find_node_by_tag("name"),
                    ref_hook.find_node_by_tag("script")
                )

                # Validate both
                if ( (ref_name != None) and (ref_script != None) ):

                    # Hash by hook name.
                    # Note that this means a duplicate will completely overwrite its predecessor.
                    self.hooks[ ref_name.innerText ] = Script( ref_script.innerText )


    # Get name
    def get_name(self):

        # Return
        return self.name


    # Get title
    def get_title(self):

        # Return
        return self.title


    # Get description
    def get_description(self):

        # Return
        return self.description


    # Check to see if this achievement is still active
    def is_active(self):

        # Active?
        return (self.status == ACHIEVEMENT_STATUS_ACTIVE)


    # Check to see if this achievement is complete
    def is_complete(self):

        # Complete?
        return (self.status == ACHIEVEMENT_STATUS_COMPLETE)


    # Get achievement status as a string
    def get_status(self):

        # Active?
        if (self.status == ACHIEVEMENT_STATUS_ACTIVE):

            # Active
            return "Active"

        # Complete?
        elif (self.status == ACHIEVEMENT_STATUS_COMPLETE):

            # Complete
            return "Complete"

        # Failed...
        elif (self.status == ACHIEVEMENT_STATUS_FAILED):

            # Failed
            return "Failed"

        # ???
        else:

            # Unknown
            return "Unknown"


    # Set this achievement's status
    def set_status(self, status):

        # Set as active?
        if (status == "active"):

            # Set as active
            self.status = ACHIEVEMENT_STATUS_ACTIVE

        # Set as complete?
        elif (status == "complete"):

            # Set as complete
            self.status = ACHIEVEMENT_STATUS_COMPLETE

        # Set as failed?
        elif (status == "failed"):

            # Set as failed
            self.status = ACHIEVEMENT_STATUS_FAILED


    # Check to see if this achievement uses a given hook
    def has_hook(self, name):

        # Simple check
        return (name in self.hooks)


    # Get a given hook (by hook name)
    def get_hook(self, name):

        # Validate
        if ( name in self.hooks ):

            # Return raw script data
            return self.hooks[name]

        # Couldn't find that hook
        else:

            # Return null
            return None
