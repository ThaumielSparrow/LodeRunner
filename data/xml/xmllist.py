import os
import re

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

    def __init__(self, tag_type):

        self.tag_type = tag_type

        self.attributes = {}

        self.nodes = []
        self.innerText = ""


    def debug(self, indent = 0):

        for i in range(0, 4 * indent):
            print " ",

        print "[%s]" % self.tag_type

        for i in range(0, 4 * indent):
            print " ",

        print "attributes:"

        for x in self.attributes:
            for i in range(0, 4 * indent + 4):
                print " ",

            print "" + x + " = " + self.attributes[x]


        for i in range(0, 4 * indent):
            print " ",

        print "children:"

        for y in self.nodes:
            y.debug(indent + 1)

        for i in range(0, 4 * indent):
            print " ",

        print "innerXML:  " + self.innerText

        print "\n"


    def add_node(self, node):

        self.nodes.append(node)

        return self.nodes[-1]


    def add_nodes(self, nodes):

        for node in nodes:

            self.add_node(node)

        # For chaining
        return self.nodes[-1] # Probably won't have much cause to use this?


    def set_attribute(self, key, value):
        #print "key = %s\nvalue = %s\n" % (key, value)
        self.attributes[key] = value

        # For chaining
        return self


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


    def compile_xml_string(self, prefix = ""):

        xml = prefix + "<%s" % self.tag_type

        for key in self.attributes:
            xml += " %s = '%s'" % (key, self.attributes[key])

        # Any children?
        if (len(self.nodes) > 0):

            xml += ">\n"

            for each in self.nodes:
                xml += each.compile_xml_string("\t" + prefix)

            xml += prefix + "</%s>\n" % self.tag_type

        # Inner text?
        elif (self.innerText != ""):

            xml += ">%s</%s>\n" % (self.innerText, self.tag_type)

        # Nope; self-closing...
        else:

            xml += " />\n"

        return xml


    def compile_inner_xml_string(self, prefix = ""):

        xml = ""

        # Any children?
        if (len(self.nodes) > 0):

            for each in self.nodes:
                xml += each.compile_xml_string("\t" + prefix)

        # Inner text?
        elif (self.innerText != ""):

            xml += self.innerText


        return xml


    def compile_xml_abstract(self, prefix = ""):

        xml = prefix + "<%s" % self.tag_type

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


    def create_node_from_xml(self, xml):

        # Create a new root node
        node = XMLNode("xml-root")

        # Parse into that node...
        self.parse_xml(xml, node)

        # Return the new node
        return node


    # If the XML contains more than one "root" node, this function will ignore all except the first...
    def convert_xml_to_one_node(self, xml):

        # Create a temporary root node
        node = XMLNode("temp")

        # Parse into that node
        self.parse_xml(xml, node)

        # Return the first node in the temp node
        return node.get_nodes_by_tag("*")[0]


    def parse_xml(self, xml, parent):

        # Strip comments from the markup
        xml = re.sub("\<\!\-\-[^$]*?\-\-\>", "", xml)

        # Strip whitespace surrounding new lines, remove tabs, excess whitespace, etc.
        xml = re.sub("[ \t]+?\n[ \t]+?", "\n", xml).strip(" \n").replace("\t", "")


        # Begin by finding the first element
        a = xml.find("<")
        b = -1

        if (a >= 0):
            b = self.find_tag_end(xml, a)

        while (a >= 0):

            # Get the style of tag
            self_closing = (xml[b - 1] == "/")


            # Get the contents of the XML
            s = xml[a + 1 : b].strip()

            # For self-closing tags, let's ditch the closing /
            if (self_closing):
                s = xml[a + 1 : b - 1].strip()


            # Split to calculate (1) tag type, and (2) tag attributes
            pieces = s.split(" ", 1)


            # We definitely will have a tag type...
            tag_type = pieces[0].strip()

            #print tag_type


            # Create a new node
            node = XMLNode(tag_type)


            # Strip any whitespace surrounding = in the attributes...
            if (len(pieces) > 1):

                pieces[1] = escape_special_characters( re.sub("[ ]+=[ ]+", "=", pieces[1]).strip() )

                # Check any attribute assignments...
                assignments = pieces[1].split(" ")

                for each in assignments:

                    kv = each.split("=")

                    # boolean attribute?
                    if (len(kv) == 1):

                        (key, value) = (kv[0], True)

                        node.set_attribute(key, value)

                    else:

                        (key, value) = (kv[0].strip(), kv[1].strip())

                        # String assignment?
                        if (value[0] == "'"):

                            value = unescape_special_characters(value).strip("'")

                            special = False
                            if (len(value) > 0):
                                if (value[0] == "@"):
                                    special = True

                            if (0 and special):
                                node.set_attribute(key, eval(value[1:len(value)]))

                            else:
                                node.set_attribute(key, value)

                        else:
                            print node.compile_xml_string()
                            print (key, value)
                            node.set_attribute(key, int(value))



            z = 0

            # For self-closing tags, don't bother looking for descendants...
            if (self_closing):
                z = b

            else:

                # Find the closing tag for this tag...
                z = self.find_tag_close(xml, a, tag_type)

                # Get the data inside...
                innerXML = xml[b + 1 : z]


                # Parse the innerXML for children
                self.parse_xml(innerXML, node)


                # If we didn't find any child nodes, take the innerXML as raw text data...
                if (len(node.nodes) == 0):
                    node.innerText = innerXML.strip()



            parent.nodes.append(node)





            # Find the next node...
            #z = self.find_tag_close(xml, a, tag_type)

            a = xml.find("<", z + 1)

            b = self.find_tag_end(xml, a)




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

        return i

    # Find the tag close position...
    def find_tag_close(self, xml, start, tag_type):

        count = 1

        while (count > 0):

            # Find the next start tag of the given type...
            a = xml.find("<%s" % tag_type, start + 1)

            if (a >= 0):

                a_end = self.find_tag_end(xml, a + 1)
                a_self_closing = xml[a_end - 1] == "/"

                while (a >= 0 and a_self_closing):

                    a = xml.find("<%s" % tag_type, a_end)

                    a_end = self.find_tag_end(xml, a + 1)
                    a_self_closing = xml[a_end - 1] == "/"

            # Find the next closing tag of the given type...
            b = xml.find("</%s" % tag_type, start + 1)

            # If we find no start tag, we must default to the end tag we found...
            if (a < 0):

                count -= 1

                if (count <= 0):
                    return b

                else:
                    start = b


            # If the start tag appeared first, we must increment our count variable
            # and continue searching...
            elif (a < b):
                count += 1
                start = a

            elif (b < a):
                count -= 1

                if (count <= 0):
                    return b

                else:
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
                print "Could not find close of XML tag; exiting."
                return

            # Get the content of the tag.  Remove any newlines...
            content = xml[pos + 1 : end].lstrip().rstrip().replace("\r\n", " ")

            #print content

            pieces = content.split(" ", 1)

            # The tag must have data
            if (len(pieces) < 2):
                print "Bad XML tag; no data; exiting."
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
                    print "Could not find close tag for '<%s>'" % tag_type

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
                        print "Bad attribute assignment operator; exiting."
                        return


            # If we had any innerxml, hack it into the attributes as the "innerxml" key.
            if (innerxml):
                attributes["innerxml"] = innerxml


            self.collection[tag_type].append(attributes)

            #print self.collection

            # Continue to the next tag
            pos = xml.find("<", pos_close_tag + 1)
