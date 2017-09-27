import random
import copy

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, xml_encode, xml_decode, ssv_unpack

from code.constants.inventory import *


"""
Typical item costs:                     Warehouses:                             Upgrade pools:

    Level 1:  25 - 75 gold              warehouse1, warehouse1+                 pool1
    Level 1+: 60 - 120 gold             warehouse2, warehouse2+                 pool2
                                        warehouse3, warehouse3+                 pool3
    Level 2:  75 - 125 gold                                                     poolSpecial
    Level 2+: 100 - 150 gold            quest, puzzle1, puzzle2, puzzle3

    Level 3:  150 - 200 gold
    Level 3+: 200 - 250 gold
"""


# A local convenience function for initializing default attributes
# for an item / item upgrade.
def generate_default_item_attributes():

    return {
        "player-speed-modifier": 0,                     # Percentage, +/- n%
        "dig-length-bonus": 0,                          # % dig duration
        "enemy-trapped-length-bonus": 0,                # % enemy trap time
        "enemy-respawn-wait-bonus": 0,                  # % enemy respawn timer
        "enemy-first-movement-wait-bonus": 0,           # % map enter movement delay
        "enemy-carrying-gold-movement-penalty": 0,      # % enemy speed when carrying gold.  Supercedes ordinary movement rate?
        "enemy-never-carries-gold": 0,                  # 1 means enemies never pick up gold
        "enemy-explode-on-death-chance": 0.0,           # % chance enemy explodes like a bomb on death
        "enemy-speed-modifier": 0.0,                    # % enemy speed
        "skill-recharge-adjustment": 1.0,               # n seconds faster (or slower, in theory)
        "reverse-kill-probability": 0.0,                # n% chance for enemy to die when he touches you
        "gold-pickup-player-speed-bonus": 0,            # % adjustment to player speed after getting gold
        "gold-pickup-player-speed-bonus-duration": 0,   #   duration of that adjustment
        "gold-pickup-enemy-speed-bonus": 0,             # % adjustment to enemy speed after player picks up gold
        "gold-pickup-enemy-speed-bonus-duration": 0,    #   duration of that adjustment
        "gold-pickup-jackpot-chance": 0,                # % chance to win a jackpot each time you pick up a piece of gold
        "gold-pickup-jackpot-amount": 0,                #   number of extra pieces of gold you get
        "bomb-replenishment-adjustment": 0,             # Earn n bombs for each enemy you kill with a bomb
        "bomb-player-immunity": 0,                      # 1 for bomb immunity
        "bomb-enemy-immunity": 0,                       # 1 for enemy immunity.  Not a good thing, probably...
        "bomb-fuse-bonus": 0,                           # % adjustment to duration of a bomb's fuse
        "player-gravity-bonus": 0,                      # % adjustment to player gravity (faster/slower)
        "enemy-gravity-bonus": 0                        #   same adjustment for enemies
    }


# Items the player can equip for various bonuses (or penalties, in some cases)
class InventoryItem:

    def __init__(self):

        self.name = ""

        self.title = "Unnamed Item"
        self.category = "Normal Item"

        self.description = "n/a"    # Full item description
        self.ad = ""                # Abstract (for prize ads)


        # Is this a cloned object?  The universe starts with blueprint objects, i.e. not cloned.
        # When the player equips an item, we actually clone the blueprint, grab upgrades, and then equip that clone.
        self.cloned = False


        # Item quality rating
        self.quality = 0

        # Item cost
        self.cost = 0

        # Item sell value (?)
        self.sell_value = 0


        """ "Constant" item upgrade data (not tracked in session) """
        # How many times can you upgrade this item?
        self.upgrades_allowed = 1 # Default

        # Which upgrade pool(s) can this item draw possible upgrades from?
        self.available_upgrade_pools_by_name = []


        """ "Variable" item upgrade data (tracked in session) """
        # How many times have we upgraded this item?
        self.upgrades_committed = 0

        # Which upgrades can we choose from?
        # We'll randomly populate this list based on the available pools at time of item acquisition.
        self.available_upgrades = []

        # Which upgrade(s) have we committed to this item?
        self.committed_upgrades = []


        # Which warehouses stock this item?
        self.warehouses = []


        # An item can offer various benefits... typically only one at a time, except for rare items...
        self.attributes = generate_default_item_attributes()

        # Track the original default value of each item.  This way, when I save the universe,
        # I'm not writing a ton of unmodified values to the file each time...
        self.attribute_defaults = generate_default_item_attributes()
        #self.attribute_defaults = {}
        #for key in self.attributes:
        #    self.attribute_defaults[key] = self.attributes[key]


        # Most items work "all the time."  These items will not use the timer attribute, thusly.
        # However, some items only work in response to a singular event, such as picking up a piece of gold.
        # These items will only take effect while the timer is online (i.e. greater than 0).
        self.timer = 0


    # Configure
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "title" in options ):
            self.title = options["title"]


        if ( "cloned" in options ):
            self.cloned = ( int( options["cloned"] ) == 1 )


        if ( "quality" in options ):
            self.quality = int( options["quality"] )

        if ( "cost" in options ):
            self.cost = int( options["cost"] )

        if ( "sell-value" in options ):
            self.sell_value = int( options["sell-value"] )


        if ( "category" in options ):
            self.category = options["category"]

        if ( "description" in options ):
            self.description = options["description"]

        if ( "ad" in options ):
            self.ad = options["ad"]


        if ( "attributes" in options ):

            # Copy each value over
            for key in options["attributes"]:

                # Make sure to cast value as float, just to be sure
                self.attributes[key] = float( options["attributes"][key] )


        if ( "warehouses" in options ):

            # Track
            self.warehouses.extend(
                options["warehouses"]
            )


        if ( "upgrades-allowed" in options ):
            self.upgrades_allowed = int( options["upgrades-allowed"] )

        if ( "upgrade-pools" in options ):

            # Track
            self.available_upgrade_pools_by_name.extend(
                options["upgrade-pools"]
            )


        if ( "upgrades-committed" in options ):
            self.upgrades_committed = int( options["upgrades-committed"] )


        #if ( "active" in options ):
        #    self.active = (int( options["active"] ) == 1)


        # For chaining
        return self

        #self.upgrades_allowed = 1
        #self.available_upgrade_pools_by_name = []
        #self.upgrades_committed = 0
        #self.available_upgrades_by_name = []
        #self.committed_upgrades_by_name = []


    # Save an item's state
    def save_state(self):

        # Container
        node = XMLNode("item")


        # Attributes
        node.add_node( XMLNode("name").set_inner_text( xml_encode(self.name) ) )
        node.add_node( XMLNode("title").set_inner_text( xml_encode(self.title) ) )
        node.add_node( XMLNode("quality").set_inner_text( xml_encode("%d" % self.quality) ) )
        node.add_node( XMLNode("cost").set_inner_text( xml_encode("%d" % self.cost) ) )
        node.add_node( XMLNode("upgrades-allowed").set_inner_text( xml_encode("%d" % self.upgrades_allowed) ) )
        node.add_node( XMLNode("description").set_inner_text( xml_encode(self.description) ) )

        # I still track committed upgrades count as an attribute, why??
        node.set_attributes({
            "upgrades-committed": xml_encode( "%d" % self.upgrades_committed ),
        })



        # Add warehouses
        node2 = node.add_node(
            XMLNode("warehouses")
        )

        # Add each warehouse
        for name in self.warehouses:

            # Add warehouse
            node2.add_node(
                XMLNode("warehouse").set_inner_text(name)
            )


        # Add upgrade pools
        node2 = node.add_node(
            XMLNode("upgrade-pools")
        )

        # Add each warehouse
        for name in self.available_upgrade_pools_by_name:

            # Add warehouse
            node2.add_node(
                XMLNode("upgrade-pool").set_inner_text(name)
            )


        # Add an attributes node, keeping a handle to it
        node2 = node.add_node(
            XMLNode("attributes")
        )

        # Add in each "non-default" attribute
        for attribute in self.attributes:

            # Make sure it's not default (0 or whatever); no point in redundantly saving default values
            if (self.attributes[attribute] != self.attribute_defaults[attribute]):

                # Create a node for this attribute pair
                local_node = node2.add_node(
                    XMLNode("attribute")
                )


                # Add key
                local_node.add_node(
                    XMLNode("key").set_inner_text(
                        xml_encode(attribute)
                    )
                )

                # Add value
                local_node.add_node(
                    XMLNode("value").set_inner_text(
                        xml_encode( "%s" % self.attributes[attribute] )
                    )
                )
                """
                # Track in attributes node
                node2.add_node(
                    XMLNode("attribute").set_attributes({
                        "key": xml_encode( attribute ),
                        "value": xml_encode( "%s" % self.attributes[attribute] ) # Cast attribute value as string
                    })
                )
                """


        # Add an upgrades node, keeping a handle
        node2 = node.add_node(
            XMLNode("upgrades")
        )


        # Indent
        if (node2):

            # Add a node for available upgrades; keep handle
            node3 = node2.add_node(
                XMLNode("available")
            )

            # Track each available upgrade
            for upgrade in self.available_upgrades:

                # Add state
                node3.add_node(
                    upgrade.save_state()
                )


            # Now add a node for committed upgrades; keep handle again
            node3 = node2.add_node(
                XMLNode("committed")
            )

            # Track each committed upgrade
            for upgrade in self.committed_upgrades:

                # Add state
                node3.add_node(
                    upgrade.save_state()
                )


        # Return state
        return node


    # Load an item's state
    def load_state(self, node):

        # Prepare to set options
        options = {}


        # Basic properties
        for prop in ("name", "title", "quality", "cost", "upgrades-allowed", "description"):

            # Look for child node containing the given data
            child = node.find_node_by_tag(prop)

            # Validate
            if (child):

                # Read in setting
                options[prop] = child.innerText
            #if ( node.get_attribute(prop) ):
            #    options[prop] = xml_decode( node.get_attribute(prop) )


        # I am still storing upgrades committed as an item attribute, why??
        if ( node.has_attribute("upgrades-committed") ):

            # Read in attribute
            options["upgrades-committed"] = node.get_attribute("upgrades-committed")


        # Find warehouses
        ref_warehouses = node.find_node_by_tag("warehouses")

        # Validate
        if (ref_warehouses):

            # Set up list
            options["warehouses"] = []

            # Loop
            for ref_warehouse in ref_warehouses.get_nodes_by_tag("warehouse"):

                # Add warehouse
                options["warehouses"].append(
                    ref_warehouse.innerText
                )


        # Find upgrade pools
        ref_upgrade_pools = node.find_node_by_tag("upgrade-pools")

        # Validate
        if (ref_upgrade_pools):

            # Set up list
            options["upgrade-pools"] = []

            # Loop
            for ref_upgrade_pool in ref_upgrade_pools.get_nodes_by_tag("upgrade-pool"):

                # Add warehouse
                options["upgrade-pools"].append(
                    ref_upgrade_pool.innerText
                )


        # Find item attributes
        ref_attributes = node.find_node_by_tag("attributes")

        # Loop attributes
        if (ref_attributes):

            # Prepare attribute options
            options["attributes"] = {}


            # Find all attributes
            attribute_collection = ref_attributes.get_nodes_by_tag("attribute")

            # Loop
            for ref_attribute in attribute_collection:

                (ref_attribute_key, ref_attribute_value) = (
                    ref_attribute.find_node_by_tag("key"),
                    ref_attribute.find_node_by_tag("value")
                )

                # Validate key/value both found
                if ( (ref_attribute_key) and (ref_attribute_value) ):

                    # Convenience
                    (key, value) = (
                        ref_attribute_key.innerText,
                        ref_attribute_value.innerText
                    )

                    # Track
                    options["attributes"][key] = value


        # Configure item
        self.configure(options)


        # Check for upgrade data
        ref_upgrades = node.get_first_node_by_tag("upgrades")

        # Load upgrade data
        if (ref_upgrades):

            # Find available / committed upgrades
            (ref_available_upgrades, ref_committed_upgrades) = (
                ref_upgrades.get_first_node_by_tag("available"),
                ref_upgrades.get_first_node_by_tag("committed")
            )


            # Check available
            if (ref_available_upgrades):

                # Grab all upgrades
                upgrade_collection = ref_available_upgrades.get_nodes_by_tag("upgrade")

                # Loop
                for upgrade in upgrade_collection:

                    # Create a new upgrade item
                    item = UpgradePoolItem()

                    # Load state on the upgrade item
                    item.load_state(upgrade)

                    # Save the upgrade as available
                    self.available_upgrades.append(item)


            # Check committed
            if (ref_committed_upgrades):

                # Grab all upgrades
                upgrade_collection = ref_committed_upgrades.get_nodes_by_tag("upgrade")

                # Loop
                for upgrade in upgrade_collection:

                    # Create a new upgrade item
                    item = UpgradePoolItem()

                    # Load state on the upgrade item
                    item.load_state(upgrade)

                    # Save the upgrade as committed
                    self.committed_upgrades.append(item)



    # Clone an item (used when acquiring an item... add a copy into the player's inventory)
    def clone(self):

        # Simple copy
        clone = copy.deepcopy(self)

        # Configure as cloned, then return
        return clone.configure({
            "cloned": True
        })


    # Get item name
    def get_name(self):

        return self.name


    # Get item title
    def get_title(self):

        return self.title


    # Get item cost
    def get_cost(self):

        return self.cost


    # Get item sell value
    def get_sell_value(self):

        return self.sell_value


    # Calculate how many more upgrades this item has available
    def count_remaining_upgrades(self):

        # Allowed versus committed
        return (self.upgrades_allowed - self.upgrades_committed)


    # Add an available upgrade
    def add_available_upgrade(self, upgrade):

        # Track
        self.available_upgrades.append(upgrade)


    # Get all available upgrades
    def get_available_upgrades(self):

        # Here you go
        return self.available_upgrades


    # Get a singular available upgrade by name
    def get_available_upgrade_by_name(self, name):

        # Loop available
        for upgrade in self.available_upgrades:

            # Match?
            if (upgrade.name == name):

                # Return
                return upgrade


        # 404
        return None

    # Commit an upgrade, removing it from available upgrades
    def commit_and_disavow_upgrade_by_name(self, name):

        # Validate that this upgrade exists in the available upgrades.
        # When found, remove it...
        pos = -1

        # Loop to search
        for i in range( 0, len(self.available_upgrades) ):

            # Match?
            if (self.available_upgrades[i].name == name):

                # Good
                pos = i


        # Validate that we can use this upgrade
        if (pos >= 0):

            # Remove from available upgrades; save a handle so that we can add it to the committed upgrades
            upgrade = self.available_upgrades.pop(pos)

            # Let's clone it into the committed upgrades list
            self.committed_upgrades.append(
                upgrade.clone()
            )


            # Increment committed upgrade tally
            self.upgrades_committed += 1


    # Get all committed upgrades
    def get_committed_upgrades(self):

        # HEre they are.  These are upgrade objects, not mere names...
        return self.committed_upgrades


    # Get item "description."  This will include any committed upgrade.
    def get_description(self):

        # Start with base description
        description = self.description


        # Do we have upgrades?
        if (self.upgrades_committed > 0):

            # Extra space
            description += "\n"

            # Loop each committed upgrade
            for upgrade in self.committed_upgrades:

                # Add "title" (basically attributes) to the description
                description += "\n%s" % upgrade.get_title()


        # Finished!
        return description


    # Inherit the attributes of any committed upgrade.  Only cloned objects can use this method;
    # the original object definitions should remain unchanged throughout the game.
    def inherit_committed_upgrades(self):

        # Only clones can do this!
        if (self.cloned):

            # Loop through each committed upgrade
            for upgrade in self.get_committed_upgrades():

                # Absort each attribute
                for key in self.attributes:

                    # A simple sanity test
                    if ( key in upgrade.attributes ):

                        # Absorb!
                        self.attributes[key] += upgrade.attributes[key]


        # Debug, more than anything
        else:
            log( "Warning:  Base, uncloned item attempted to inherit committed upgrades." )


    # Set an item's timer value (used on cloned items, i.e. equipped items)
    def set_timer(self, timer):

        # Track
        self.timer = timer


    # Check to see if this item is "active" (i.e. timer has a value greater than 0).
    # Some objects work all the time, but others will only take effect for a given duration.
    def is_active(self):

        # Check
        return (self.timer > 0)


    # Run any logic related to collecting a piece of gold
    def handle_gold_collection(self, control_center, universe):

        # Does the player move faster after collecting gold?
        if ( self.attributes["gold-pickup-player-speed-bonus"] > 0 ):

            # Duration always measured in seconds
            self.timer = (60 * self.attributes["gold-pickup-player-speed-bonus-duration"])

            # Invalidate any cached player speed calculation (force refresh)
            universe.invalidate_item_attribute_result("player-speed")


    # Process an item (used on cloned items, i.e. equipped items)
    def process(self):

        # Do we have an active timer?
        if (self.timer > 0):

            # Tick
            self.timer -= 1

            # Expired?
            if (self.timer <= 0):

                # Expired status
                return ITEM_PROCESS_RESULT_EXPIRED

            else:
                return ITEM_PROCESS_RESULT_NORMAL

        else:
            return ITEM_PROCESS_RESULT_NORMAL


class UpgradePool:

    def __init__(self):

        # Track pool name
        self.name = ""

        # Track the upgrades available in this pool
        self.upgrades = []


    # Configure pool
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]


        # For chaining
        return self


    # Save pool state
    def save_state(self):

        # Container
        node = XMLNode("upgrade-pool")


        # Remember name
        node.set_attributes({
            "name": xml_encode( self.name )
        })


        # Add all upgrades
        for upgrade in self.upgrades:

            # Append child node
            node.add_node(
                upgrade.save_state()
            )


        # Return
        return node


    # Load pool state
    def load_state(self, node):

        # Prepare to set options
        options = {}


        # Basic properties
        for prop in ("name",):

            if ( node.get_attribute(prop) ):
                options[prop] = xml_decode( node.get_attribute(prop) )


        # Configure pool
        self.configure(options)


        # Seek all upgrades
        upgrade_collection = node.get_nodes_by_tag("upgrade")

        # Loop
        for ref_upgrade in upgrade_collection:

            # Create a new upgrade item
            item = UpgradePoolItem()

            # Set its state based on the reference
            item.load_state(ref_upgrade)

            # Add it to this pool
            self.add(item)


    # Add an upgrade
    def add(self, item):

        # Append
        self.upgrades.append(item)


    # Get upgrades
    def get_upgrades(self):

        # Here you og
        return self.upgrades


class UpgradePoolItem:

    def __init__(self):

        # Upgrade option name
        self.name = ""

        # Upgrade option title (i.e. caption)
        self.title = ""


        # How much does it cost to select this upgrade?
        self.cost = 0


        # Attributes used by this upgrade
        self.attributes = generate_default_item_attributes()

        # Track the original default value of each item upgrade.  This way, when I save the universe,
        # I'm not writing a ton of unmodified values to the file each time...
        self.attribute_defaults = {}

        for key in self.attributes:
            self.attribute_defaults[key] = self.attributes[key]


    # Configure the upgrade
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "title" in options ):
            self.title = options["title"]

        if ( "cost" in options ):
            self.cost = int( options["cost"] )


        # Check for attribute data
        if ( "attributes" in options ):

            # Copy key by key
            for key in options["attributes"]:

                # Save as floats
                self.attributes[key] = float( options["attributes"][key] )


        # For chaining
        return self


    # Save state
    def save_state(self):

        # Container
        node = XMLNode("upgrade")


        # Track name
        node.set_attributes({
            "name": xml_encode( self.name )
        })


        # Add title / caption
        node.add_node(
            XMLNode("title").set_inner_text( self.title )
        )

        # Add cost
        node.add_node(
            XMLNode("cost").set_inner_text( "%s" % self.cost ) # Cast as string
        )


        # Add a node for attributes, keep a handle
        node2 = node.add_node(
            XMLNode("attributes")
        )


        # Save each non-default attribute
        for attribute in self.attributes:

            # Make sure it's not default (0 or whatever); no point in redundantly saving default values
            if (self.attributes[attribute] != self.attribute_defaults[attribute]):

                # Create a node for this attribute pair
                local_node = node2.add_node(
                    XMLNode("attribute")
                )


                # Add key
                local_node.add_node(
                    XMLNode("key").set_inner_text(
                        xml_encode(attribute)
                    )
                )

                # Add value
                local_node.add_node(
                    XMLNode("value").set_inner_text(
                        xml_encode( "%s" % self.attributes[attribute] )
                    )
                )

                """
                # Track in attributes node
                node2.add_node(
                    XMLNode("attribute").set_attributes({
                        "key": xml_encode( attribute ),
                        "value": xml_encode( "%s" % self.attributes[attribute] ) # Cast attribute value as string
                    })
                )
                """


        # Return state
        return node


    # Load state
    def load_state(self, node):

        # Prepare to set options
        options = {}


        # Basic properties
        for prop in ("name",):

            if ( node.get_attribute(prop) ):
                options[prop] = xml_decode( node.get_attribute(prop) )


        # Details
        (ref_title, ref_cost, ref_attributes) = (
            node.get_first_node_by_tag("title"),
            node.get_first_node_by_tag("cost"),
            node.get_first_node_by_tag("attributes")
        )


        if (ref_title):
            options["title"] = ref_title.innerText

        if (ref_cost):
            options["cost"] = ref_cost.innerText


        # Loop attributes
        if (ref_attributes):

            # Prepare attribute options
            options["attributes"] = {}


            # Find all attributes
            attribute_collection = ref_attributes.get_nodes_by_tag("attribute")

            # Loop
            for ref_attribute in attribute_collection:

                (ref_attribute_key, ref_attribute_value) = (
                    ref_attribute.find_node_by_tag("key"),
                    ref_attribute.find_node_by_tag("value")
                )

                # Validate key/value both found
                if ( (ref_attribute_key) and (ref_attribute_value) ):

                    # Convenience
                    (key, value) = (
                        ref_attribute_key.innerText,
                        ref_attribute_value.innerText
                    )

                    # Track
                    options["attributes"][key] = value


        # Configure upgrade
        self.configure(options)


    # Clone an item upgrade (used when acquiring an item... add a copy to the new item we create for the player's inventory)
    def clone(self):

        # Simple copy
        return copy.deepcopy(self)


    # Get name
    def get_name(self):

        return self.name


    # Get title
    def get_title(self):

        return self.title


    # Get cost
    def get_cost(self):

        return self.cost
