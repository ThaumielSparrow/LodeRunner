import random

from code.tools.xml import XMLNode

from code.utils.common import log, log2, logn, xml_encode, xml_decode

class Conversation:

    def __init__(self):

        self.id = ""

        # A conversation will have at least one branch: root.  It may have additional
        # branches (dependent responses) that we access later on in the same conversation.
        # We'll load all of them at runtime.
        self.branches = {} # Key by branch id (e.g. "root")


    # Take a <conversation /> node and parse out the conversation's ID
    # along with any dialogue branch that falls within this conversation.
    def import_conversation_data_from_node(self, node, recursive = False):

        # The first call to this function (before we employ recursion) provides a <conversation />
        # node which contains the conversation's ID.
        if (not recursive):

            # Let's validate, just for fun
            if ( node.tag_type == "conversation" ):

                # Ok.  Grab ID.
                self.id = "%s" % node.get_attribute("id")


        # Now let's grab all child nodes.  (We'll only really care about <branch /> nodes, but we will recur into most other nodes.)
        node_collection = node.get_nodes_by_tag("*")

        # Check each...
        for ref_node in node_collection:

            # If it's a <branch> node, then of course we'll load in branch data...
            if (ref_node.tag_type == "branch"):

                logn( "conversation debug", "Found '%s' within <%s>" % (ref_node.get_attribute("id"), node.tag_type) )

                # Key by branch id (e.g. "root")
                self.branches[ ref_node.get_attribute("id") ] = ConversationBranch().import_lines_from_branch_node( ref_node )

                if ( ref_node.get_attribute("id") == "root.bye" ):
                    logn( "conversation debug", ref_node.compile_xml_string().replace("\n", " ") )

                # Check for any nested branch within this branch (e.g. <branch><branch /></branch>)...
                self.import_conversation_data_from_node(ref_node, recursive = True)

            # If it's not a <branch> node, we'll most likely still recur into it, scouring for any nested branch nodes within... (e.g. responses have nested <branch> nodes)
            else:

                # One exception:  Don't recur into any nested conversation, because those conversations
                # are entirely self-contained and irrelevant to the current conversation.
                # (I only store the conversations inside another conversation to keep related
                # conversations together in the raw dialogue file.)
                if (ref_node.tag_type == "conversation"):
                    pass

                else:

                    # Check for nested branches
                    self.import_conversation_data_from_node(ref_node, recursive = True)


        # For chaining
        return self


    # Save conversation state data
    def save_state(self):

        # Create node
        node = XMLNode("conversation")

        # Set properties
        node.set_attributes({
            "id": xml_encode( "%s" % self.id )
        })

        # Loop branches
        for branch_id in self.branches:

            # Add branch state
            node.add_node(
                self.branches[branch_id].save_state()
            )

        # Return node
        return node


    # Load conversation state data
    def load_state(self, node):

        # Loop branches
        for ref_branch in node.get_nodes_by_tag("branch"):

            # Branch id
            branch_id = ref_branch.get_attribute("id")

            # Validate that the branch exists
            if (branch_id in self.branches):

                # Recall memory data
                self.branches[branch_id].load_state(ref_branch)

            else:
                log2( "Warning:  Conversation '%s' does not contain branch '%s'" % (self.id, branch_id) )


    # Get all lines (across all branches) that match a given class name
    def get_lines_by_class(self, param):

        # Track results
        results = []

        # Loop branches
        for key in self.branches:

            # Get results for this branch
            results.extend(
                self.branches[key].get_lines_by_class(param)
            )

        # Return results
        return results


    def update_lines_and_responses_by_selector(self, selector, active):

        for key in self.branches:

            self.branches[key].update_lines_and_responses_by_selector(selector, active)


    # Get a branch in this conversation by its id
    def get_branch_by_id(self, branch_id):

        # Validate
        if (branch_id in self.branches):

            # Return branch object
            return self.branches[branch_id]

        else:
            return None


class ConversationBranch:

    def __init__(self):

        self.id = ""

        # A branch may have any number of linear responses
        self.linear_data = []

        # It may also have any number of nag responses
        self.nag_data = []


        # Where in the linear branch are we?
        self.linear_position = 0


    # Pull in all of the lines that apply to this branch of the conversation.
    # Some are delivered in linear order; others are delivered randomly (nags).
    def import_lines_from_branch_node(self, node):

        # The initial <branch /> node will contain the ID of the branch.
        # We'll keep it around...
        if ( node.tag_type == "branch" ):

            # Track
            self.id = node.get_attribute("id")


        # See if we have any linear data
        ref_linear_data = node.get_first_node_by_tag("linear")

        if (ref_linear_data):

            # Find all linear lines
            line_collection = ref_linear_data.get_nodes_by_tag("line")

            # Loop
            for ref_line in line_collection:

                # Create a new Line object for the line
                self.linear_data.append(
                    ConversationBranchLine().import_comment_and_responses_from_node( ref_line )
                )


        # See if we have any nag data...
        ref_nag_data = node.get_first_node_by_tag("nags")

        if (ref_nag_data):

            # Get all nag lines
            line_collection = ref_nag_data.get_nodes_by_tag("line")

            # Looper
            for ref_line in line_collection:

                # Create a new Line object for the line
                self.nag_data.append(
                    ConversationBranchLine().import_comment_and_responses_from_node( ref_line )
                )


        # For chaining
        return self


    # Save branch state data
    def save_state(self):

        # Create node
        node = XMLNode("branch")

        # Set properties
        node.set_attributes({
            "id": xml_encode( "%s" % self.id ),
            "linear-position": xml_encode( "%d" % self.linear_position )
        })


        # Add data for all lines.
        # I used to only do this for named lines / lines with named responses, but now I automatically id each line, so it would save them all anyway.
        # I don't know why I didn't/don't wrap these in a container node.
        for line in self.linear_data + self.nag_data:

            # Add state
            node.add_node(
                line.save_state()
            )

        # Return node
        return node


    # Load branch state
    def load_state(self, node):

        # Recall position
        if ( node.has_attribute("linear-position") ):
            self.linear_position = int( node.get_attribute("linear-position") )

        # Loop all line states
        for ref_line in node.get_nodes_by_tag("line"):

            # Line id
            line_id = ref_line.get_attribute("id")

            # Loop all lines, we'll find it somewhere...
            for line in self.linear_data + self.nag_data:

                # Match?
                if (line.id == line_id):

                    # Load line state
                    line.load_state(ref_line)


    # Get all lines
    def get_lines(self):

        return self.linear_data + self.nag_data


    # Get all lines with a given class
    def get_lines_by_class(self, param):

        # Wildcard returns all lines
        if (param == "*"):

            logn( "conversation debug", "Checking ... all... results:  %s" % self.get_lines() )

            # Return all
            return self.get_lines()

        # Otherwise, find explicit matches
        else:

            # Track results
            results = []

            # Loop lines
            for line in self.get_lines():

                # Match?
                if ( line.has_class(param) ):

                    # Track
                    results.append(line)

            logn( "conversation debug", "Checking ... results:  %s" % results )

            # Return results
            return results


    def update_lines_and_responses_by_selector(self, selector, active):

        # Are we looking for an id selector or a class selector?
        if (selector.startswith("#")):

            # What to compare against?
            param = selector.lstrip("#")

            # Check each line (and each response therein) for the given ID...
            for line in self.linear_data + self.nag_data:

                # Check the line itself
                if (line.id == param):

                    line.active = active

                # Check each response
                for response in line.responses:

                    if (response.id == param):

                        response.active = active

        # Class selector...
        elif (selector.startswith(".")):

            # Which class to check?
            param = selector.lstrip(".")

            # Check each line...
            for line in self.linear_data + self.nag_data:

                # Check the line itself
                log( "Compare line#%s against param '%s'" % (line.class_name, param) )
                if (line.class_name == param):

                    line.active = active
                    log( "\tUpdated" )

                # Check each response
                for response in line.responses:

                    log( "Compare response#%s against param '%s'" % (response.class_name, param) )
                    if (response.class_name == param):

                        response.active = active
                        log( "\tUpdated to:  %s" % response.active )


    # Get a line in this branch by its id.
    # Search both linaer and nag data.  Used for scripting, when looking to enable/disable certain responses.
    def get_line_by_id(self, line_id):

        # Check all lines, linear and nag
        for line in self.linear_data + self.nag_data:

            # Return first match, regardless of active/inactive/unread state.
            if (line.id == line_id):

                # Matched
                return line


        # 404
        return None
        

    def get_next_line(self):

        # We always present all of the linear dialogue before presenting
        # nag data.  Thusly, let's loop each linear line.
        for line in self.linear_data:

            # We can only select from active and unread lines
            if ( (line.active) and (line.unread) ):

                # Mark this line as read (or, "not unread") before we return it
                line.unread = False

                # Increment total reads
                line.increment_total_reads()

                # Return line data object
                return line


        # If we didn't find an active/unread linear line,
        # then let's look at the nag data.  If possible,
        # we'll return a fresh, unread nag.  However, we'll
        # return an "old" nag if we have no alternative.
        unread_nag_indices = []
        active_nag_indices = []

        # Loop by index
        for i in range( 0, len(self.nag_data) ):

            # Track all active, whether read or unread.
            # However, ignore lines that we have read the "max" number of times.
            if (
                (self.nag_data[i].active) and
                ( (self.nag_data[i].max_reads <= 0) or (self.nag_data[i].total_reads < self.nag_data[i].max_reads) )
            ):

                # Track as active
                active_nag_indices.append(i)

                # if the player hasn't read this one, then track it also as unread
                if (self.nag_data[i].unread):

                    # Track as active and unread
                    unread_nag_indices.append(i)


        # Hopefully we can return a fresh nag
        if ( len(unread_nag_indices) > 0 ):

            # Find the highest priority level of any unread nag line.
            # Typically they all will have 0 (default), but sometimes...
            max_priority = max( self.nag_data[i].get_priority() for i in unread_nag_indices )

            # Filter out any line falling under max priority
            i = 0
            while ( i < len(unread_nag_indices) ):

                # Not of the highest priority, huh?
                if ( self.nag_data[ unread_nag_indices[i] ].get_priority() < max_priority ):

                    # Goodbye
                    unread_nag_indices.pop(i)

                # Priority ok
                else:
                    i += 1


            # Select a line data object at random (from the remaining eligible nag lines)
            line = self.nag_data[ unread_nag_indices[ random.randint(0, len(unread_nag_indices) - 1) ] ]

            # Quickly mark as read ("not unread")
            line.unread = False

            # Increment total reads
            line.increment_total_reads()

            # Return line object
            return line

        # Usually we can at least return a random "old" nag
        elif ( len(active_nag_indices) > 0 ):

            # Select a line data object at random
            line = self.nag_data[ active_nag_indices[ random.randint(0, len(active_nag_indices) - 1) ] ]

            # Increment total reads on the previously-read line
            line.increment_total_reads()

            # Return line object
            return line

        # Well, I guess we have nothing to return at all.
        else:

            return None

        """
        # See if we're still in line for linear conversation lines...
        if (self.linear_position < len(self.linear_data)):

            # Move ahead in anticipation of future chats
            self.linear_position += 1

            # Skip inactive lines...
            while ( (self.linear_position <= len(self.linear_data)) and (self.linear_data[ self.linear_position - 1 ].active == False) ):

                self.linear_position += 1


            # Did we run out of linear lines?
            if (self.linear_position > len(self.linear_data)):

                # Try to get a nag line instead...
                return self.get_next_line()

            else:

                # Reference the previous value to get the currently requested line
                return self.linear_data[ self.linear_position - 1 ]

        # No; do we have nag data?
        elif ( len(self.nag_data) > 0 ):

            # Figure out which nags we can use (active nags)
            eligible = []

            for i in range(0, len(self.nag_data)):

                if (self.nag_data[i].active):

                    eligible.append(i)


            # No nag available?
            if (len(eligible) == 0):

                return None

            # Pick one at random...
            else:

                index = random.randint(0, len(eligible) - 1)

                return self.nag_data[ eligible[index] ]

        # No nag data; no chatting available...
        else:

            return None
        """


class ConversationBranchLine:

    def __init__(self):

        # We'll store the line's ID soon (e.g. "line1")
        self.id = ""

        # Class name.  Useful for enabling/disabling multiple lines at once (e.g. disabled all lines of class "i-like-you").  Optional...
        self.class_name = ""

        # Priority level defaults to 0.  A nag line with higher priority will appear sooner when unread, but then in standard rotation.
        self.priority = 0


        # A line will (almost?) always have a comment (e.g. "How are you?")
        self.comment = ""

        # A line may have any number of responses; it may have no response.
        self.responses = []


        # A line may or may not be active...
        self.active = True

        # Track whether or not the player has read this line.
        self.unread = True

        # Optionally, we can set a limit on the number of times an NPC
        # will use a given line.
        self.max_reads = 0

        # If the NPC has a limit on the number of times they can use this line,
        # we'll count the number of times we have read this line.
        self.total_reads = 0


        # We can put a temporary lock on a given line
        # to prevent it from being enabled/disabled.
        # This is not saved as part of a line's state, though.
        self.locked = False


        # A line may trigger a certain script (e.g. increase infamy upon a certain insult)
        self.script = None


        # It may also immediately run script data within the dialogue sequence
        self.pre_inject_script_name = None


        self.pre_script = None

        self.post_script = None


        # A line may redirect to another branch (e.g. back to root conversation after buying some bombs)
        self.redirect = None

        # A line may have some other miscellaneous attributes as well
        self.attributes = {}


    # Take a <line /> node and extract the NPC comment, various line properties, and any
    # possible response (e.g. Yes; No; Maybe later...) the line might offer.
    def import_comment_and_responses_from_node(self, node):

        # Get ID
        if ( node.tag_type == "line" ):

            # If the node specifies an id, then grab it.
            # We expect every line to have an id, but we don't explicitly require it.
            # (Many will have an autogenerated id, e.g. line-autoid-####.)
            if ( node.has_attribute("id") ):

                # Read in id
                self.id = "%s" % node.get_attribute("id")


            # Class name?
            if (node.get_attribute("class")):

                self.class_name = node.get_attribute("class")

            # Priority level?
            if (node.get_attribute("priority")):

                self.priority = int( node.get_attribute("priority") )

            # Active?
            if (node.get_attribute("active")):

                self.active = ( int( node.get_attribute("active") ) == 1 )

            # Max reads?
            if ( node.has_attribute("max-reads") ):

                # Set
                self.max_reads = int( node.get_attribute("max-reads") )


            # Attached script?
            if (node.get_attribute("script")):

                self.script = node.get_attribute("script")

            # Pre-inject?
            if (node.get_attribute("pre-inject")):

                self.pre_inject_script_name = node.get_attribute("pre-inject")

            # Redirect?
            if (node.get_attribute("redirect")):

                self.redirect = node.get_attribute("redirect")


            # Check for pre-scripts;
            ref_pre_script = node.get_first_node_by_tag("pre-script")

            if (ref_pre_script):

                self.pre_script = ref_pre_script


            # and post-scripts.
            ref_post_script = node.get_first_node_by_tag("post-script")

            if (ref_post_script):

                self.post_script = ref_post_script


            # Computer dialogue lines may include references to a few other attributes...
            extended_attributes = ("transition", "back-button-text", "responses-header-text", "use-grid", "per-row")

            for key in extended_attributes:

                # Default to empty string for these...
                self.attributes[key] = ""

                # See if we can find a specified value
                if ( node.get_attribute(key) ):

                    self.attributes[key] = xml_decode( node.get_attribute(key) )


        # Minimum hacking?
        if ( node.get_attribute("min-hacking") ):

            self.min_hacking = int( node.get_attribute("min-hacking") )

        # Minimum persuasion?
        if ( node.get_attribute("min-persuasion") ):

            self.min_persuasion = int( node.get_attribute("min-persuasion") )

        # Minimum gold?
        if ( node.get_attribute("min-gold") ):

            self.min_gold = int( node.get_attribute("min-gold") )


        # Get the line comment (e.g. "Hi player, thanks for talking to me!")
        ref_comment = node.get_first_node_by_tag("comment")

        if (ref_comment):

            # Save comment text
            self.comment = ref_comment.innerText


        # Get any possible response
        response_collection = node.get_nodes_by_tag("response")

        # Loop
        for ref_response in response_collection:

            self.responses.append(
                ConversationBranchLineResponse().import_response_data_from_node( ref_response )
            )


        # For chaining
        return self


    # Save line state
    def save_state(self):

        # Create node
        node = XMLNode("line")

        # Set properties
        node.set_attributes({
            "id": xml_encode( "%s" % self.id ),
            "active": xml_encode( "%d" % self.active ),
            "unread": xml_encode( "%d" % self.unread ),
            "total-reads": xml_encode( "%d" % self.total_reads )
        })

        # Loop responses
        for response in self.responses:

            # I used to only save "named" responses, but really every response should point to a branch-id, so let's just save them all.
            # I don't know why I didn't/don't put these in a container node.
            node.add_node(
                response.save_state()
            )

        # Return node
        return node


    # Load line state
    def load_state(self, node):

        # Recall active status?
        if ( node.has_attribute("active") ):

            # Update
            self.active = ( int( node.get_attribute("active") ) == 1 )

        # Recall unread status?
        if ( node.has_attribute("unread") ):

            # Update
            self.unread = ( int( node.get_attribute("unread") ) == 1 )

        # Recall total number of reads?
        if ( node.has_attribute("total-reads") ):

            # Update
            self.total_reads = int( node.get_attribute("total-reads") )

        # debug
        log( "%s = %d" % (self.id, self.active) )


        # Get response nodes, if/a
        response_collection = node.get_nodes_by_tag("response")

        # Loop response nodes
        for ref_response in response_collection:

            # What's the ID?
            response_id = ref_response.get_attribute("id")

            # Try to find that response
            response = self.get_response_by_id(response_id)


            # Validate
            if (response):

                # Load response state
                response.load_state(ref_response)


    # Get enabled (i.e. active) status
    def get_enabled(self):

        # Line active?
        return self.active


    # Set enabled status (boolean)
    def set_enabled(self, enabled):

        # Update active status accordingly
        self.active = enabled


    def get_attribute(self, key):

        if (key in self.attributes):

            return self.attributes[key]

        else:
            return ""


    # Get priority level
    def get_priority(self):

        # Return
        return self.priority


    # Check to see if this line has a given class name
    def has_class(self, class_name):

        logn( "conversation debug", "Checking 'line.%s' for class name '%s'" % (self.class_name, class_name) )

        # A line can have more than one class.
        for s in self.class_name.split(" "):

            # Check match
            if ( s.strip() == class_name ):

                # Match
                return True

        # Does not have the given class
        return False


    def get_response_by_id(self, response_id):

        for response in self.responses:

            if (response.id == response_id):

                return response

        # Couldn't find it...
        return None


    def get_responses(self):

        responses = []

        for response in self.responses:

            # Ignore "hidden" responses (prefixed with a dash)
            if ( not response.is_hidden() ):

                if (response.active):

                    responses.append(response)

        return responses


    def get_responses_by_class(self, class_name):

        # If class name is a wildcard, immediately return all responses
        if (class_name == "*"):

            logn( "conversation debug", "Checking ... all ... results:  %s" % self.responses )

            # Match all
            return self.responses

        # Otherwise, check class on each
        else:

            # Track results
            responses = []

            # Loop responses
            for response in self.responses:

                # Match class name?
                if ( response.has_class(class_name) ):

                    # Add to results
                    responses.append(response)

            logn( "conversation debug", "Checking ... results:  %s" % responses )

            # Return results
            return responses


    # Enable this line
    def enable(self):

        # Not locked?
        if (not self.locked):

            # Active
            self.active = True


    # Disable this line
    def disable(self):

        # Not locked?
        if (not self.locked):

            # Inactive
            self.active = False


    # Lock this response.  Prevents enable/disable
    # calls from taking effect.
    def lock(self):

        # Set as locked
        self.locked = True


    # Increment the number of times we have read this line
    def increment_total_reads(self):

        # Don't bother incrementing unless this line has a limit
        if (self.max_reads > 0):

            # Simple increment
            self.total_reads += 1


class ConversationBranchLineResponse:

    def __init__(self):

        # The key to the next dialogue branch (e.g. root.line1:yes)
        self.id = ""

        # Class name?  Optional...
        self.class_name = ""


        # The phrase visible to the player (e.g. "Yes I want to buy the bombs")
        self.phrase = "(Undefined response)"

        # Some dialogue panels (e.g. computer panels) will reference additional details from a response line for display
        self.details = ""


        # Response active?
        self.active = True

        # A response might be hidden (mainly used a computers for "intro" messages)
        self.hidden = False

        # "Error" message (e.g. "Not enough gold!")
        self.error_phrase = ""


        # A response may require a certain level of skill in Hacking or Persuasion
        self.min_hacking = 0
        self.min_persuasion = 0

        # Minimum gold for certain responses (e.g. purchases)
        self.min_gold = 0


        # Track whether or not to translate the text of the response.
        # By default we will translate.
        self.translate = True


    # Take a <response /> node and extract the response text, ID, etc.
    def import_response_data_from_node(self, node):

        # Validate
        if ( node.tag_type == "response" ):

            #print node.compile_xml_string()
            #print 5/0

            # Get ID of the branch we'll move to when selecting this response
            self.id = "%s" % node.get_attribute("branch-id")

            # Class name?
            if ( node.get_attribute("class") ):
                self.class_name = node.get_attribute("class")


            # Get visible phrase (e.g. "I accept the quest!")
            ref_phrase = node.get_first_node_by_tag("phrase")

            if (ref_phrase):

                self.phrase = "%s" % ref_phrase.innerText


            # Get response details
            ref_details = node.get_first_node_by_tag("details")

            if (ref_details):

                # I'm going to store the details as plain text until we need it for a dialogue panel
                self.details = "%s" % ref_details.compile_inner_xml_string()


            # Active?
            if ( node.get_attribute("active")):

                self.active = ( int( node.get_attribute("active") ) == 1 )

            # Hidden?
            if ( node.get_attribute("hidden")):

                self.hidden = ( int( node.get_attribute("hidden") ) == 1 )


            # Minimum hacking?
            if ( node.get_attribute("min-hacking")):

                self.min_hacking = int( node.get_attribute("min-hacking") )

            # Minimum persuasion?
            if ( node.get_attribute("min-persuasion")):

                self.min_persuasion = int( node.get_attribute("min-persuasion") )

            # Minimum gold?
            if ( node.get_attribute("min-gold")):

                self.min_gold = int( node.get_attribute("min-gold") )


            # Translate?
            if ( node.has_attribute("translate") ):

                # Update setting
                self.translate = (int( node.get_attribute("translate") ) == 1)


        # For chaining
        return self


    # Save response state
    def save_state(self):

        # Create node
        node = XMLNode("response")

        # Set properties
        node.set_attributes({
            "branch-id": xml_encode( "%s" % self.id ),
            "active": xml_encode( "%d" % self.active )
        })

        # Return node
        return node


    # Load response state
    def load_state(self, node):

        log( "Loading memory for response '%s'" % self.id )
        log( "\t%s\n" % xml.compile_xml_string() )

        if ( node.has_attribute("active") ):
            self.active = ( int( node.get_attribute("active") ) == 1 )

        log( "\t%s = %d" % (self.id, self.active) )


    def is_hidden(self):

        return self.hidden


    # Enable this response
    def enable(self):

        # Active
        self.active = True


    # Disable this response
    def disable(self):

        # Inactive
        self.active = False


    # Check to see if this response has the requested class
    def has_class(self, class_name):

        logn( "conversation debug", "Checking 'response.%s' for class name '%s'" % (self.class_name, class_name) )

        # Split class name string by space, support multiple classes
        for s in self.class_name.split(" "):

            # Match?
            if ( s.strip() == class_name ):

                # Yes
                return True

        # Never matched
        return False

