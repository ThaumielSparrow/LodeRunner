import os

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser

from code.utils.common import log, log2, logn, xml_encode, xml_decode


class XMLTemplate:

    # Constructor
    def __init__(self):

        # Track xml structure
        self.template = ""

        # For debugging
        self.last_filepath = ""


        # Track registered data parameters
        self.data_parameters = []

        # Track registered text parameters
        self.text_parameters = []


        # Track supplied parameters in a hash
        self.user_parameters = {}


    # Set template data
    def set_template_data(self, template):

        # Update
        self.template = template


    # Add a data parameter
    def add_data_parameter(self, name):

        # Update list
        self.data_parameters.append(name)


    # Add a text parameter
    def add_text_parameter(self, name):

        # Update list
        self.text_parameters.append(name)


    # Add parameters as key/value hash.
    # We will use this data to update a template before compiling the final widget.
    def add_parameters(self, h):

        # Update known data hash
        self.user_parameters.update(h)


        # For chaining
        return self


    # Compile a given node in the existing template data
    def compile_node_by_id(self, node_id):

        # Copy template as working markup
        markup = self.template


        # Keep track of "text" parameters (secondary translations) in a simple hash.
        # We won't translate these values until after we've compiled the widget.
        translations = {}


        # Loop supplied parameter data
        for key in self.user_parameters:

            # Is this a registered data parameter?
            if (key in self.data_parameters):

                # Replace known data parameters in the template data.
                # We translate these literals before compiling into a widget.
                markup = markup.replace(key, self.user_parameters[key])

            # Is this a registered data parameter?
            # We'll add it to the translations hash for future use.
            elif (key in self.text_parameters):

                # Track
                translations[key] = self.user_parameters[key]

            # Unregistered.  Print a simple warning...
            else:
                logn(5, "Warning:  Unknown template parameter '%s' in template '%s'" % (key, self.last_filepath))


        # Build the node from markup, then find the requested node id.
        node = XMLParser().create_node_from_xml(markup).find_node_by_id(node_id)


        # Lastly, set the "translations" data value to hold the
        # text translations (only translated after widget creation).
        node.set_data("translations", translations)


        # Return node
        return node


    # Compile a given layout node in the existing template data,
    # then return the appropriate layout result.
    def compile_layout_by_id(self, node_id, control_center):

        # Get all layouts
        node = self.compile_node_by_id(node_id)

        # Validate that this is a layout node
        if ( node.tag_type == "layouts" ):

            # Scope
            node2 = None


            # Try to find node matching current layout
            ref = node.find_node_by_tag( control_center.get_localization_controller().get_layout() )

            # Validate
            if (ref):

                # Get first match
                node2 = ref.get_first_node_by_tag("*")

            # Fall back to potential default
            else:

                # Try to find "else" node
                ref = node.find_node_by_tag("else")

                # Validate
                if (ref):

                    # Get first node
                    node2 = ref.get_first_node_by_tag("*")


            # Did we find the desired layout?
            if (node2):

                # Share translations (share reference)
                node2.set_data( "translations", node.get_data("translations") )

                # Return located layout
                return node2


        # If anything fails, return the full layouts node.
        return node


class UITemplateLoaderExt:

    def __init__(self):

        return


    # Fetch an XML template by name at the default location.  If a template has variations, the "version" param will dictate which one we return...
    def fetch_xml_template(self, name, version = None):

        self.last_filepath = name

        return self.fetch_xml_template_from_path(
            name,
            os.path.join("data", "xml", "templates"),
            version
        )


    # Fetch an XML template by name from a given path
    def fetch_xml_template_from_path(self, name, path, version = None):

        # Prepare new XMLTemplate object
        template = XMLTemplate()


        # Construct disk path
        path = os.path.join(path, "%s.xml" % name)


        # Validate
        if (os.path.exists(path)):

            f = open(path, "r")
            data = f.read()
            f.close()


            # Build xml node from data
            root = XMLParser().create_node_from_xml(data)


            # First, find all of this template's registered parameters.
            ref_parameters = root.find_node_by_tag("parameters")

            # Validate
            if (ref_parameters):

                # Data parameters
                ref_data_parameters = ref_parameters.find_node_by_tag("data")

                # Validate
                if (ref_data_parameters):

                    # Loop all
                    for ref_parameter in ref_data_parameters.get_nodes_by_tag("parameter"):

                        # Track new data parameter
                        template.add_data_parameter(ref_parameter.innerText)


                # Text parameters
                ref_text_parameters = ref_parameters.find_node_by_tag("text")

                # Validate
                if (ref_text_parameters):

                    # Loop all
                    for ref_parameter in ref_text_parameters.get_nodes_by_tag("parameter"):

                        # Track new text parameter
                        template.add_text_parameter(ref_parameter.innerText)


            # Multiple templates?  "version" param will dictate which one we want...
            if (version != None):

                # Find the right one...
                node = root.get_first_node_by_tag(
                    "template",
                    {
                        "version": xml_encode(version)
                    }
                )

                # Validate
                if (node):

                    # Set template data
                    template.set_template_data(
                        node.compile_xml_string(include_namespaces = True)
                    )

            # Default to first listed template
            else:

                # Find first overall node
                node = root.get_first_node_by_tag("template")

                # Validate
                if (node):

                    # Set template data
                    template.set_template_data(
                        node.compile_xml_string(include_namespaces = True)
                    )

                # If no "template" tag exists, take the first available tag...
                else:

                    # We'll take anything at this point
                    node = root.get_first_node_by_tag("*")

                    # Validate
                    if (node):

                        # Set template data
                        template.set_template_data(
                            node.compile_xml_string(include_namespaces = True)
                        )


        # Return XMLTemplate object
        return template


    # Parameterize a given XML template
    def parameterize_xml_template(self, xml, params = {}):

        # Replace params
        for key in params:
            xml = xml.replace(key, params[key])

        return xml


# A class can inherit from this to designate itself as "hookable,"
# such that event-handling objects can "hook" into it and receive
# a copy of an event the inheriting widget receives.
class HookableExt:

    def __init__(self):

        # Keep track of any object that hooks into us.  Hash by active status; we'll remove inactive (value == False)
        # listenerss after the forward-event call, in case forwarding the event itself prompts an unhook.
        self.listeners = {}

        # Before we loop through the listeners, we'll lock the "caller."  If anything wants to hook into
        # the caller during a "broadcast," it will have to wait in the queue until the original dispatch concludes.
        self.listener_queue = []

        # Lock count
        self.ext_hook_lock_count = 0


    # Get listeners
    def get_listeners(self):

        return self.listeners


    # Lock
    def ext_hook_lock(self):

        self.ext_hook_lock_count += 1


    # Unlock
    def ext_hook_unlock(self):

        self.ext_hook_lock_count -= 1

        # Don't go negative
        if (self.ext_hook_lock_count < 0):
            self.ext_hook_lock_count = 0


    # Check lock status
    def ext_hook_is_locked(self):

        # Simple check
        return (self.ext_hook_lock_count > 0)


    # Hook up with a new object
    def hook(self, listener):

        # If not locked...
        if ( not self.ext_hook_is_locked() ):

            # Set as active
            self.listeners[listener] = True

        # Otherwise, wait for a moment...
        else:

            self.listener_queue.append(listener)


    # Remove a hook
    def unhook(self, listener):

        # Validate
        if (listener in self.listeners):

            # Designate as ready for removal
            self.listeners[listener] = False


    # Convenience for forwarding an event to each listener
    def forward_event_to_listeners(self, event, control_center, universe):

        # Resultant events
        results = EventQueue()


        # Lock while we forward
        self.ext_hook_lock()

        # Message each listener
        for listener in self.get_listeners():

            # Forward event, track results
            results.append(
                listener.handle_event(event, control_center, universe)
            )

        # We're done forwarding, so we will unlock
        self.ext_hook_unlock()


        # Let's see if anything decides to jump into the queue while we forwarded that event
        while ( len(self.listener_queue) > 0 ):

            # Safe to hook it in, now...
            self.hook(
                self.listener_queue.pop()
            )


        # Check for unhooked (inactive) listeners
        keys = self.listeners.keys()

        for key in keys:

            # Is the given listener inactive?
            if ( self.listeners[key] == False ):

                log( "Removing listener..." )
                self.listeners.pop(key)


        # Return events
        return results
