import os
import re

from code.utils.common import log, log2, logn, xml_encode, xml_decode

def escape_quoted_whitespace(s):
    in_quote = False
    new_string = ""

    for i in range(0, len(s)):

        if (s[i] == "'"):
            in_quote = (not in_quote)

        if (s[i] == " "):
            if (in_quote):
                new_string += "&nbsp;"
            else:
                new_string += s[i]

        else:
            new_string += s[i]

    return new_string

def unescape_quoted_whitespace(s):
    return s.replace("&nbsp;", " ")



def escape_special_characters(s):

    # Which characters will we replace?
    translations = {
        " ": "&nbsp;",
        "<": "&lt;",
        ">": "&gt;",
        "=": "&equals;" # I think I'm making this up...
    }


    # Track when we're within a string (which needs the escape)
    in_quote = False

    # Remember translated output
    output = ""


    for i in range(0, len(s)):

        # Toggle
        if (s[i] == "'"):
            in_quote = (not in_quote)

            output += s[i]

        elif (s[i] in translations):

            if (in_quote):
                output += translations[ s[i] ]

            else:
                output += s[i]

        else:
            output += s[i]


    return output

def unescape_special_characters(s):

    reverse_translations = {
        "&nbsp;": " ",
        "&lt;": "<",
        "&gt;": ">",
        "&equals;": "="
    }

    for key in reverse_translations:
        s = s.replace(key, reverse_translations[key])

    return s




class XMLNode:

    def __init__(self, tag_type, tag_namespace = None):

        # Node type (e.g. "box" for "<box />")
        self.tag_type = tag_type

        # Node namespace (optional)
        self.tag_namespace = tag_namespace


        # Node attributes (serialized)
        self.attributes = {}

        # HIdden data properties (not serialized)
        self.data = {}


        # Children
        self.nodes = []


        # Inner content
        self.innerText = ""
        self.innerXml = ""


        # A node will have knowledge of its parent.
        # Of course, top-level nodes will not have a parent.
        self.parent = None


    def debug(self, indent = 0):

        for i in range(0, 4 * indent):
            log( " ", )

        log( "[%s]" % self.tag_type )

        for i in range(0, 4 * indent):
            log( " ", )

        log( "attributes:" )

        for x in self.attributes:
            for i in range(0, 4 * indent + 4):
                log( " ", )

            log( "" + x + " = " + self.attributes[x] )


        for i in range(0, 4 * indent):
            log( " ", )

        log( "children:" )

        for y in self.nodes:
            y.debug(indent + 1)

        for i in range(0, 4 * indent):
            log( " ", )

        log( "innerXML:  " + self.innerText )

        log( "\n" )


    def add_node(self, node):

        self.nodes.append(node)

        # Set parent on the new node!
        self.nodes[-1].set_parent(self)

        return self.nodes[-1]


    def add_nodes(self, nodes):

        for node in nodes:

            self.add_node(node)

        # For chaining
        return self.nodes[-1] # Probably won't have much cause to use this?


    # Set parent for this node
    def set_parent(self, parent):

        # Set
        self.parent = parent


    # Get parent for this node
    def get_parent(self):

        # Return
        return self.parent


    # Get this node's namespace
    def get_namespace(self):

        # Return
        return self.tag_namespace


    def set_attribute(self, key, value):

        # Set attribute
        self.attributes[key] = value

        # For chaining
        return self


    # Check to see if a node has a given attribute
    def has_attribute(self, key):

        return (key in self.attributes)


    def get_attribute(self, key):

        if (key in self.attributes):
            return self.attributes[key]

        else:
            return False


    # Set many attributes in one call
    def set_attributes(self, attribute_hash):

        for key in attribute_hash:

            self.set_attribute(key, attribute_hash[key])

        # For chaining
        return self


    # Get all attributes
    def get_attributes(self):

        return self.attributes


    # Check to see if a node has a given data value key
    def has_data(self, key):

        return (key in self.data)


    # Set data value for a given key
    def set_data(self, key, value):

        # Set
        self.data[key] = value

        # For chaining
        return self


    # Get data value for a given key
    def get_data(self, key):

        # Validate
        if ( self.has_data(key) ):

            # Return stored data
            return self.data[key]


        # Not found
        return None


    def get_inner_text(self):

        # Return
        return self.innerText


    def set_inner_text(self, text):

        self.innerText = text

        # For chaining
        return self


    def get_node_by_id(self, node_id):

        for node in self.nodes:

            if (node.get_attribute("id")):

                if (node.get_attribute("id") == node_id):

                    return node

        return None


    def get_nodes_by_tag(self, tag, params = None):

        output = []

        for node in self.nodes:

            if (node.tag_type == tag or tag == "*"):

                # No need to qualify
                if (not params):
                    output.append(node)

                # Check for parameter match
                else:

                    for key in params:

                        if (node.attributes[key] == params[key]):
                            output.append(node)

        return output


    def get_nodes_by_tags(self, tags, params = None):

        output = []

        for node in self.nodes:

            tag_pieces = tags.split(",")

            for i in range(0, len(tag_pieces)):
                tag_pieces[i] = tag_pieces[i].strip()

            for tag in tag_pieces:

                if (node.tag_type == tag or tag == "*"):

                    # No need to qualify
                    if (not params):
                        output.append(node)

                    # Check for parameter match
                    else:

                        for key in params:

                            if (node.attributes[key] == params[key]):
                                output.append(node)

        return output


    def get_first_node_by_tag(self, tag, params = None):

        nodes = self.get_nodes_by_tag(tag, params)


        if (len(nodes) > 0):

            return nodes[0]

        else:

            return None


    # Find a node by a given id.  We'll check the first-level descendants first, then recur into children sequentially.
    def find_node_by_id(self, node_id):

        # Check direct descendants
        for node in self.nodes:

            # Match?
            if ( node.get_attribute("id") == node_id ):

                return node


        # If we still haven't matched, we'll try to recur through each child...
        for node in self.nodes:

            # See if we can find it later on in the hierarchy
            descendant = node.find_node_by_id(node_id)

            # Did we find a match?
            if (descendant):

                # We'll return this match.
                return descendant


        # If we've gone through every node descending from this node and we still haven't
        # found the node, then we just can't find it.
        return None


    # Remove a node by a given XMLNode object
    def remove_node(self, node):

        # Loop descendants
        i = 0
        while ( i < len(self.nodes) ):

            # Object match?
            if ( self.nodes[i] == node ):

                # Goodbye
                return self.nodes.pop(i)

            # Loop
            i += 1

        """
        # Grandchildren check?
        """

        # Couldn't find that node
        return None


    # Remove a node by a given id, plus all of its children (obviously, I guess)
    def remove_node_by_id(self, node_id):

        # Check direct descendants
        i = 0
        while ( i < len(self.nodes) ):

            # If this is the one, we'll remove it and all of its children
            if ( self.nodes[i].get_attribute("id") == node_id ):

                # Later dude.  Return the removed node for a last chance to do something with it...
                return self.nodes.pop(i)

            # Loop
            i += 1


        # If we didn't match a direct descendant, check grandchildren...
        for node in self.nodes:

            # Try to remove it from the descendant...
            removed_grandchild = node.remove_node_by_id(node_id)

            # If we removed one successfully, then we received the removed node...
            if (removed_grandchild):

                # Bubble it back to the original request
                return removed_grandchild


        # If we have reached the end of the line, then I guess we can't find a node by that id...
        return None


    # Find the first node (at any depth) that matches a given tag name
    def find_node_by_tag(self, tag_type):

        # Check direct descendants
        for node in self.nodes:

            # Match?
            if ( node.tag_type == tag_type ):

                return node


        # If we still haven't matched, we'll try to recur through each child...
        for node in self.nodes:

            # See if we can find it later on in the hierarchy
            descendant = node.find_node_by_tag(tag_type)

            # Did we find a match?
            if (descendant):

                # We'll return this match.
                return descendant


        # If we've gone through every node descending from this node and we still haven't
        # found the node, then we just can't find it.
        return None


    # Find the "deepest" node of a given tag type.
    # Deepest in this case means it has no nested tag of the same type; we'll still return the first possible match (e.g. 2nd-generation will return instead of 5th-generation
    #   if it appears "higher" in a flat readout.)
    def find_deepest_node_by_tag(self, tag_type):

        # Check direct descendants
        for node in self.nodes:

            # Match?
            if ( node.tag_type == tag_type ):

                # Now let's check for a deeper node by recursively calling this same function.
                node2 = node.find_deepest_node_by_tag(tag_type)

                # If we found a deeper node, we'll return it instead.  (This logic ensures that we ultimately return a node with no nested children of the same tag type.)
                if (node2):

                    # Return the deepest match
                    return node2

                # Otherwise, return this direct descendant; it has no children of the same type, so it's the "deepest" in its branch.
                else:

                    # Return this match
                    return node


        # Failing a direct descendant match, we'll check each descendant's children (grandchildren check)
        for node in self.nodes:

            # Check for grandchild node
            node2 = node.find_deepest_node_by_tag(tag_type)

            # Did we find a match?
            if (node2):

                # Return match
                return node2


        # Could not find a node of that type anywhere in the tree
        return None


    # Find all nodes that match a given tag, even searching recursively if desired
    def find_nodes_by_tag(self, tag_type, recursive = False):

        # Matches
        results = []

        # Loop children
        for node in self.nodes:

            # Child match?
            if ( node.tag_type == tag_type ):

                # Track result
                results.append(node)


            # Always recur, if/a
            if (recursive):

                # Extend results
                results.extend(
                    node.find_nodes_by_tag(tag_type, recursive)
                )

        # Return all matches
        return results


    def compile_xml_string(self, prefix = "", include_namespaces = False, encode_innerText = True, pretty = True):

        # Assume no namespace
        tag_data = "%s" % self.tag_type

        # Check namespace inclusion flag
        if (include_namespaces):

            # Confirm that a namespace exists
            if (self.tag_namespace != None):

                # Add namespace
                tag_data = "%s:%s" % (self.tag_namespace, self.tag_type)


        # Begin serialization
        xml = prefix + "<%s" % tag_data

        for key in self.attributes:
            xml += " %s = '%s'" % (key, self.attributes[key])

        # Any children?
        if (len(self.nodes) > 0):

            # Pretty formatting?
            if (pretty):

                # Add newline
                xml += ">\n"

                # Loop through nodes and indent each one
                for each in self.nodes:
                    xml += each.compile_xml_string("\t" + prefix, include_namespaces, encode_innerText, pretty)

                # Close tag
                xml += prefix + "</%s>\n" % tag_data

            # Everything in a single line
            else:

                # Close tag without newline
                xml += ">"

                # Loop through nodes, no indention
                for each in self.nodes:
                    xml += each.compile_xml_string(prefix, include_namespaces, encode_innerText, pretty)

                # Close tag, don't add newline
                xml += prefix + "</%s>" % tag_data

        # Inner text?
        elif (self.innerText != ""):

            # If the inner text has one or more line breaks,
            # then I'm going to indent it on a new line.
            if ( self.innerText.find("\n") >= 0 ):

                # Pretty with trailing newline?
                if (pretty):
                    xml +=  ">\n%s\t%s\n%s</%s>\n" % (prefix, self.innerText.strip(), prefix, tag_data)

                # No newline
                else:
                    xml +=  ">\n%s\t%s\n%s</%s>\n" % (prefix, self.innerText.strip(), prefix, tag_data)

            # Otherwise, I'm going to print it out without any indenting...
            else:

                # I don't always want to encode the inner text data
                if (encode_innerText):

                    # Pretty with trailing newline?
                    if (pretty):
                        xml += ">%s</%s>\n" % ( xml_encode( self.innerText.strip() ), tag_data )

                    # No newline
                    else:
                        xml += ">%s</%s>" % ( xml_encode( self.innerText.strip() ), tag_data )

                # Flag set to false?
                else:

                    # Pretty with trailing newline?
                    if (pretty):
                        xml += ">%s</%s>\n" % ( self.innerText, tag_data )

                    # No newline
                    else:
                        xml += ">%s</%s>" % ( self.innerText, tag_data )

        # Nope; self-closing...
        else:

            # Pretty with newline?
            if (pretty):
                xml += " />\n"

            # No newline
            else:
                xml += " />"

        return xml


    def compile_inner_xml_string(self, prefix = "", include_namespaces = False):

        xml = ""

        # Any children?
        if (len(self.nodes) > 0):

            for each in self.nodes:
                xml += each.compile_xml_string("\t" + prefix, include_namespaces)

        # Inner text?
        elif (self.innerText != ""):

            xml += xml_encode(self.innerText)


        return xml


    def compile_xml_abstract(self, prefix = "", include_namespaces = False):

        # Assume no namespace
        tag_data = "%s" % self.tag_type

        # Check namespace inclusion flag
        if (include_namespaces):

            # Confirm that a namespace exists
            if (self.tag_namespace != None):

                # Add namespace
                tag_data = "%s:%s" % (self.tag_namespace, self.tag_type)


        xml = prefix + "<%s" % tag_data

        for key in self.attributes:
            xml += " %s = '%s' " % (key, self.attributes[key])

        if (len(self.nodes) > 0):

            xml += ">"

        else:

            xml += " />"

        return xml


class XMLDocument:
    def __init__(self, xml, parent = None):

        self.nodes = {}

        #self.parse_xml(xml)

    #def clear(self):
    #    self.tag_collections = {}


class XMLParser:

    def __init__(self):
        return


    # Compile an xml string into a single xml node, wrapping the entire contents in a parent node
    def create_node_from_xml(self, xml, maxdepth = -1):

        # Create a new root node
        node = XMLNode("xml-root")

        # Parse into that node.  Return no node if the xml does not validate
        if ( not self.parse_xml(xml, node, maxdepth = maxdepth) ):

            # Abandon
            return None

        else:

            # Return the new node
            return node


    # Import a filepath into a single xml node, wrapping the file's xml contents in a parent node.  Returns a single (empty) wrapper node if file does not exist.
    def create_node_from_file(self, filepath, maxdepth = -1):

        # Create wrapper
        node = XMLNode("xml-root")


        # Validate filepath
        if ( os.path.exists(filepath) ):

            # Read file contents
            f = open(filepath, "r")
            xml = f.read()
            f.close()

            # Parse file contents.  Return no node if the parsing fails validation
            if ( not self.parse_xml(xml, node, maxdepth = maxdepth) ):

                # Abandon
                return None

        # Return the node, presumably with the file contents imported
        return node


    # If the XML contains more than one "root" node, this function will ignore all except the first...
    def convert_xml_to_one_node(self, xml):

        # Create a temporary root node
        node = XMLNode("temp")

        # Parse into that node
        self.parse_xml(xml, node)

        # Return the first node in the temp node
        return node.get_nodes_by_tag("*")[0]


    def parse_xml(self, xml, parent, depth = 1, maxdepth = -1):

        # Track whether or not we have valid xml data.  Assume we do, at the beginning.
        valid = True


        # Strip comments from the markup
        xml = re.sub("\<\!\-\-[^$]*?\-\-\>", "", xml)

        # Strip whitespace surrounding new lines, remove tabs, excess whitespace, etc.
        xml = re.sub("[ \t]+?\n[ \t]+?", "\n", xml).strip(" \n").replace("\t", "")


        """
        def gLog(args):
            for arg in args:
                print arg
        log = lambda *s: gLog(s)
        log2 = log
        logn = log
        #log(xml)
        """

        # Begin by finding the first element
        a = xml.find("<")
        b = -1

        if (a >= 0):

            b = self.find_tag_end(xml, a)

            # If we couldn't find the end of the tag, then we invalidate the entire document
            if (b < 0):

                # Just for posterity
                valid = False

                # Immediately abandon parsing for this node
                return False

            # We found the end of the intro tag.
            while (a >= 0):

                # Check to see if this is a self-closing tag ( e.g. <node /> or <node attribute = '1' /> )
                self_closing = (xml[b - 1] == "/")


                # Get the contents of the XML
                s = xml[a + 1 : b].strip()

                # For self-closing tags, let's ditch the closing /
                if (self_closing):
                    s = xml[a + 1 : b - 1].strip()


                # Split to calculate (1) tag type, and (2) tag attributes
                pieces = s.split(" ", 1)


                # We definitely will have a tag type.  We might have namespace data.
                tag_data = pieces[0].strip()

                # Assume
                (tag_namespace, tag_type) = (
                    None,
                    tag_data
                )

                # Check for namespace
                if ( tag_data.find(":") >= 0 ):

                    # Reinterpret data
                    (tag_namespace, tag_type) = tag_data.split(":", 1)


                # Create a new node using the given tag type
                node = XMLNode(tag_type, tag_namespace)


                # Strip any whitespace surrounding = in the attributes, if we actually have any attribute to read
                if (len(pieces) > 1):

                    # Remove whitespace surrounding the assignment operator ( e.g. attribute = '1' -> attribute='1' ).  This simplifies parsing.
                    pieces[1] = escape_special_characters( re.sub("[ ]+=[ ]+", "=", pieces[1]).strip() )

                    # Check any attribute assignments...
                    assignments = pieces[1].split(" ")

                    # Loop all
                    for each in assignments:

                        # Split by the assignment operator to get the key and the value
                        kv = each.split("=")

                        # If we didn't assign a value to this attribute, we'll treat it as a boolean attribute, set as True...
                        if ( len(kv) == 1 ):

                            (key, value) = (kv[0], True)

                            node.set_attribute(key, value)

                        else:

                            (key, value) = (kv[0].strip(), kv[1].strip())

                            # String assignment?
                            if (value[0] == "'"):

                                # Unescape value (?)
                                value = unescape_special_characters(value).strip("'")

                                # Save attribute
                                node.set_attribute(key, value)

                            else:

                                # (?) Save as integer
                                try:
                                    node.set_attribute(key, int(value))

                                # Can't set this attribute.  Assumed integer, but
                                # cannot convert.
                                except:
                                    pass#node.set_attribute(


                z = 0

                # For self-closing tags, don't bother looking for descendants...
                if (self_closing):
                    z = b

                else:

                    # Find the closing tag for this tag...
                    z = self.find_tag_close(xml, a, tag_data)

                    # If we couldn't find the close tag, then we'll have to invalidate the entire document
                    if (z < 0):

                        # Posterity
                        valid = False

                        logn( "xml error", tag_data + ":  could not find close tag (%s)" % a )
                        logn( "xml error", "not found in:  %s" % xml[a : a + 250].replace("\n", "<br>") )

                        # Abandon
                        return False

                    # We did indeed find the close tag
                    else:

                        # Get the data inside...
                        innerXML = xml[b + 1 : z]

                        # (Track that innerXML in a member variable)
                        # (Please note and excuse the inconsistent casing)
                        node.innerXml = innerXML


                        # Can we continue to parse?
                        if ( (maxdepth < 0) or (depth < maxdepth) ):

                            # Parse the innerXML for children.  Check validity of child node
                            valid = self.parse_xml(innerXML, node, depth = depth + 1, maxdepth = maxdepth)

                            # If the child xml didn't validate, we'll have to abort
                            if (not valid):

                                # Too bad!
                                return False

                            # It did validate
                            else:

                                # If we didn't find any child nodes, take the innerXML as raw text data...
                                if (len(node.nodes) == 0):

                                    node.innerText = xml_decode( innerXML.strip() )

                        # If not, we'll save the remaining contents are simple innerText
                        else:

                            # Save as text
                            node.innerText = xml_decode( innerXML.strip() )



                #parent.nodes.append(node)
                parent.add_node(node)





                # Find the next node...
                #z = self.find_tag_close(xml, a, tag_type)

                a = xml.find("<", z + 1)

                b = self.find_tag_end(xml, a)

        return valid

    # From the beginning of a tag, find the end of the tag.
    # (We want to skip over any > within attribute strings...)
    def find_tag_end(self, xml, start):

        in_quote = False
        i = start

        while (i < len(xml)):

            if (xml[i] == "'"):
                in_quote = (not in_quote)

            elif (xml[i] == ">"):

                if (in_quote):
                    pass

                else:
                    return i

            i += 1

        # We didn't find the end of the tag; it's apparently an invalid xml document.
        return -1

    # Find the tag close position...
    def find_tag_close(self, xml, start, tag_type):

        count = 1

        while (count > 0):

            # Find the next start tag of the given type...
            a = -1

            # Regex search
            result = re.search("<%s[ />]" % tag_type, xml[ (start+1) : len(xml) ])

            # Validate
            if (result):

                # Grab start position
                a = (start+1) + result.start()
            #a = xml.find("<%s" % tag_type, start + 1)
            #a = re.search("<%s[

            # Did we find another start tag?
            if (a >= 0):

                # Try to find the end of the tag we found
                a_end = self.find_tag_end(xml, a + 1)

                # Did we fail to find the end of that tag?
                if (a_end < 0):

                    # We'll have to abort
                    return -1

                # We did find it...
                else:

                    # Is the node we found self-closing?  (e.g. <node />)
                    a_self_closing = xml[a_end - 1] == "/"

                    # If it is, then we should just ignore it; it doesn't count for or against our search for the final end tag we want.
                    # As such, let's keep looking to see if we can find a non-self-closing start tag...
                    while (a >= 0 and a_self_closing):

                        # Look again
                        a = -1#xml.find("<%s" % tag_type, a_end)

                        # Regex search
                        result = re.search("<%s[ />]" % tag_type, xml[ a_end : len(xml) ])

                        # Validate
                        if (result):

                            # Grab start position
                            a = a_end + result.start()


                        # Try to find the end of the tag we just found, if we found one...
                        if (a >= 0):

                            # End search
                            a_end = self.find_tag_end(xml, a + 1)

                            # Did we fail to find the end of the tag?  Invalid xml, probably...
                            if (a_end < 0):

                                # Abort
                                return -1

                            # Let's see if this one is self-closing as well?
                            else:

                                # We'll keep looking until we find either a non-self-closing tag or we can't find another start tag...
                                a_self_closing = xml[a_end - 1] == "/"


            # Find the next closing tag of the given type...
            b = xml.find("</%s>" % tag_type, start + 1)


            # If we didn't find any closing tag anywhere, then this node just won't validate
            if (b < 0):

                logn( "xml error", "not found:  </%s>" % tag_type, len(xml) )
                logn( "xml error", "not found:  ... %s" % xml[start : start + 250].replace("\n", "<br>"), xml.find("\/ba9f") )

                # Abort
                return -1

            # If we did find a given close tag, we still have to validate that we found the one that closes the right one (and not a nested tag of the same tag type)
            else:

                # If we find no potentially nested start tag, we will default to the end tag we found...
                if (a < 0):

                    # Decrease nested tag penalty counter
                    count -= 1

                    # If we've found enough closing tags to offset any nested same-tag-type nodes, then we've officially found the closing tag
                    if (count <= 0):

                        # Finally!
                        return b

                    # Otherwise, we still haven't found the closing tag; we've only found the closing tag for one of the nested tags of the same tag type.
                    # We'll have to continue searching...
                    else:

                        # Keep searching beyond the closing tag we just found
                        start = b


                # If the start tag appeared first, we must increment our count variable
                # and continue searching...
                elif (a < b):

                    # We found a closing tag, but we also found a non-self-closing opening tag of the same name; this means that we have not yet found
                    # the real closing tag, but only a nested closing tag.  We must increase the penalty counter and continue our search.
                    count += 1
                    start = a

                # The closing tag appears first in the remainder, so we'll check the penalty counter to see if we have the real close tag.
                elif (b < a):

                    # Decrease nested tag penalty counter
                    count -= 1

                    # Have we finally found the real close tag?
                    if (count <= 0):

                        # Yes!
                        return b

                    # No; we must keep looking.
                    else:

                        # Not yet...
                        start = b


class XMLList:
    def __init__(self, xml):
        self.collection = {}

        self.parse_xml(xml)

    def clear(self):
        self.collection = {}

    def parse_xml(self, xml):

        # Start by finding the first tag
        pos = xml.find("<")

        while (pos >= 0):

            has_innerxml = False

            # Where's the end of this tag?
            end = xml.find("/>", pos + 1)

            if (end < 0):
                end = xml.find(">", pos + 1)

                if (end >= 0):
                    has_innerxml = True

            # Bail if we didn't find a close tag...
            if (end < 0):
                log( "Could not find close of XML tag; exiting." )
                return

            # Get the content of the tag.  Remove any newlines...
            content = xml[pos + 1 : end].lstrip().rstrip().replace("\r\n", " ")

            pieces = content.split(" ", 1)

            # The tag must have data
            if (len(pieces) < 2):
                log( "Bad XML tag; no data; exiting." )
                return

            # The first piece is the tag type
            tag_type = pieces[0]

            # Set up an empty list for this tag type if we haven't already
            if (not (tag_type in self.collection)):
                self.collection[tag_type] = []

            # The rest of the content contains the tag's attributes
            tag_attributes_string = escape_special_characters(pieces[1])



            # This xml parser may use self-containing tags <complete />
            pos_close_tag = end


            # See if we need to fetch any innerxml
            innerxml = None

            if (has_innerxml):

                pos_close_tag = xml.find("</%s>" % tag_type, end + 1)

                if (pos_close_tag < 0):
                    log( "Could not find close tag for '<%s>'" % tag_type )

                else:
                    innerxml = xml[ (end + 1) : pos_close_tag ].strip("\r\n ")

            # Gather the tag's attributes
            attributes = {}

            # Split the attribute string by " " (safe since we escapes within-quote whitespace)
            # and look for assignment operators (i.e. = signs)
            pieces = tag_attributes_string.split(" ")

            for i in range(0, len(pieces)):

                if (pieces[i] == "="):

                    # Make sure we're in bounds (e.g. <tag attribute = > will fail)
                    if (i > 0 and i < (len(pieces) - 1)):

                        key = pieces[i - 1].lstrip().rstrip()
                        value = pieces[i + 1].lstrip().rstrip()

                        # Remove the quotes and unescape any whitespace
                        value = value.lstrip("'").rstrip("'")
                        value = unescape_special_characters(value)

                        # Save the attribute
                        attributes[key] = value

                    else:
                        log( "Bad attribute assignment operator; exiting." )
                        return


            # If we had any innerxml, hack it into the attributes as the "innerxml" key.
            if (innerxml):
                attributes["innerxml"] = innerxml


            self.collection[tag_type].append(attributes)

            #print self.collection

            # Continue to the next tag
            pos = xml.find("<", pos_close_tag + 1)
