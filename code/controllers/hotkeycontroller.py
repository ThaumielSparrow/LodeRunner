import os

from code.tools.xml import XMLParser

from code.utils.common import log, log2, xml_encode, xml_decode

class HotkeyController:

    def __init__(self):

        # Track the various hotkeys and their parameters in a hash, hashed by keycode
        self.hotkeys = {}


    # Load in hotkey definitions from a given XML file
    def import_from_xml_file(self, filename):

        # Validate
        if ( os.path.exists(filename) ):
        
            # Read data
            f = open(filename, "r")
            xml = f.read()
            f.close()

            # Convert into a node
            node = XMLParser().create_node_from_xml(xml).find_node_by_id("hotkeys")

            # Validate
            if (node):

                # Find all hotkeys
                hotkey_collection = node.get_nodes_by_tag("hotkey")

                # Loop
                for ref_hotkey in hotkey_collection:

                    # Which keycode triggers this hotkey event?
                    keycode = int( xml_decode( ref_hotkey.get_attribute("keycode") ) )

                    # Create a new hotkey
                    hotkey = Hotkey()

                    # Load hotkey state
                    hotkey.load_state(ref_hotkey)

                    # Hash the hotkey by the specified keycode
                    self.hotkeys[keycode] = hotkey


    # Get hotkeys
    def get_hotkeys(self):

        return self.hotkeys


# Hotkey wrapper
class Hotkey:

    def __init__(self):

        # Event info hash (**obselete?)
        self.event_info = {}


        # Event action
        self.action = ""

        # Event params hash
        self.params = {}


    # Load hotkey state
    def load_state(self, node):

        # Find refs
        (ref_event_info, ref_action, ref_params) = (
            node.get_first_node_by_tag("event-info"),
            node.get_first_node_by_tag("action"),
            node.get_first_node_by_tag("params")
        )


        # Fetch event info params
        if (ref_event_info):

            # Collect
            hash_collection = ref_event_info.get_nodes_by_tag("*")

            # Loop
            for ref_hash in hash_collection:

                # Convenience
                (key, value) = (
                    ref_hash.tag_type,
                    ref_hash.innerText
                )

                # Track in event info hash
                self.event_info[key] = value


        # Fetch event action
        if (ref_action):

            # Grab inner text
            self.action = ref_action.innerText


        # Fetch event params... params
        if (ref_params):

            # Collect
            hash_collection = ref_params.get_nodes_by_tag("param")

            # Loop
            for ref_hash in hash_collection:

                # Convenience
                (key, value) = (
                    xml_decode( ref_hash.get_attribute("key") ),
                    xml_decode( ref_hash.get_attribute("value") )
                )

                # Track param
                self.params[key] = value


    # Get event info
    def get_event_info(self):

        return self.event_info


    # Get event action
    def get_action(self):

        return self.action


    # Get params
    def get_params(self):

        return self.params
