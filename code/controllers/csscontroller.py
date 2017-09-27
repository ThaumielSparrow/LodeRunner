import os
import sys

import re

import time

from code.utils.common import log, log2, logn, parse_rgb_from_string


# Types of selector matches
MATCH_NONE = 1
MATCH_INHERITED = 2
MATCH_PERFECT = 3

# Define select attributes that do not cascade to children
NONCASCADING_ATTRIBUTES = (
    "margin",
    "margin-top",
    "margin-bottom",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "background-alpha",
    "border-size",
    "shadow-size",
    "rounded-corners"
)

# Certain attributes (e.g. margin, padding) should distribute their value to all of their associated
# relatives (e.g. margin-top, margin-bottom or padding-top, padding-bottom).  This allows a selector
# with a higher specificity to use a generic "padding" without worrying about a less specific selector's
# "padding-bottom" attribute incorrectly superceding it.
ATTRIBUTE_RELATIONS = {

    "margin": (
        "margin-top",
        "margin-bottom"
    ),

    "padding": (
        "padding-top",
        "padding-bottom" # Skipping left/right for now, whatever
    )

}


class CSSController:

    def __init__(self):

        # Hash all of the selectors we may load in
        self.properties_by_selector = {}

        # Retain order of those selectors to determine order precedence
        self.selector_order = []


        # Trawling through all of the selectors, comparing against bloodlines... it's tedious!
        # Let's cache the results as we go for efficiency.
        self.cached_selector_properties = {}


        self.debug_count = 0


    def reset(self):

        # No known selectors now
        self.properties_by_selector = {}

        # Reset selector order
        self.selector_order = []

        # Clear cache
        self.cached_selector_properties.clear()


    # (Try to) get all matching properties for a given selector
    def get_cached_selector_properties(self, selector):
        #return None

        # Cached?
        if (selector in self.cached_selector_properties):

            # Yes!
            return self.cached_selector_properties[selector]

        # Nope
        else:

            return None


    # Cache the matching properties for a given selector phrase
    def cache_selector_properties(self, selector, properties):

        # Cache it
        self.cached_selector_properties[selector] = properties


    # Parse a CSS property ( e.g. "rgb(255, 255, 255)" -> (255, 255, 255) )
    def parse_css_property(self, p):

        # Check for bbcode definitions first
        matches = re.findall( "\[color=([^\]]+?)\]rgb\(([^)]+?)\)\[\/color\]", p )

        # 1 or more bbcode definitions?
        if ( len(matches) > 0 ):

            # Store them all in a hash
            codes = {}

            # Loop matches
            for (name, rgb_string) in matches:

                # Hash by color name
                codes[name] = parse_rgb_from_string(rgb_string)

            return codes


        # Check for generic RGB define
        matches = re.findall( "rgb\(([^)]+?)\)", p )

        # Found one?
        if ( len(matches) > 0 ):

            # Take the first result, we should only have one anyway...
            rgb_string = matches[0]

            return parse_rgb_from_string(rgb_string)


        # Check for quotes, remove if necessary
        matches = re.findall( "\"([^\"]*?)\"", p )

        # Matched?
        if ( len(matches) > 0 ):

            # Return the stuff inside the quotes
            return matches[0]


        # Default to the original property text
        return p


    # Read in a CSS file and parse its contents
    def load_selectors_from_file(self, path):

        # Validate that path exists
        if ( os.path.exists(path) ):

            # Read data
            f = open(path, "r")
            data = f.read()
            f.close()


            #data = "* { color: rgb(225, 225, 225); } container:active { border-size: 1; border: rgb(207, 106, 19); } "


            # Take lines.  I hate carriage returns.
            lines = data.replace("\r", "").split("\n")

            # First, let's remove all newlines, ignore whitespace, etc...
            i = 0
            while ( i < len(lines) ):

                # First, strip leading / trailing whitespace
                lines[i] = lines[i].strip()

                # Now strip comment data
                pos = lines[i].find("//")

                # Ignore everything >= the comment marker
                if (pos >= 0):

                    # We might end up with an empty string, which is fine...
                    lines[i] = lines[i][0:pos]

                # Strip one more time
                lines[i] = lines[i].strip()

                # If we have no data left, ignore this line
                if ( len(lines[i]) == 0 ):

                    lines.pop(i)

                # Otherwise, continue...
                else:
                    i += 1


            # Now let's cobble together all of the lines into a long single-line string...
            css = " ".join(lines)


            # grep the string for its selector / descriptor blocks
            matches = re.findall( "([^{]*?){([^}]*?)}", css )

            # Let's process the results
            for (iter_selector_phrase, iter_description) in matches:

                # First, get rid of annoying whitespace
                selectors = iter_selector_phrase.strip()
                description = iter_description.strip()


                # In case we've got comma-separated selectors, prepare a list...
                associated_selectors = []

                # Split "selector" by comma
                pieces = selectors.split(",")

                # Add each to the list
                for piece in pieces:

                    associated_selectors.append( piece.strip() )


                # Loop through each selector that inherits the given properties...
                for selector in associated_selectors:

                    # Prepare to grab selector properties
                    properties = {}

                    # We'll check each datum in the description
                    pieces = description.split(";")

                    # Each property...
                    for piece in pieces:

                        # Validate
                        if ( piece.find(":") > 0 ):

                            # Key, value...
                            (key, value) = piece.split(":", 1) # Only split one time

                            # Whitespace removal
                            key = key.strip()
                            value = value.strip()

                            # Parse and save the property
                            properties[key] = self.parse_css_property(value)


                    # If we haven't applied any properties for this selector yet, set up an empty hash...
                    if ( not (selector in self.properties_by_selector) ):

                        # Empty hash
                        self.properties_by_selector[selector] = {}


                    # Save the current selector's properties...
                    for key in properties:

                        self.properties_by_selector[selector][key] = properties[key]

                    # Track order!
                    self.selector_order.append(selector)


            # Check for "extensions" to the base css template.
            # Begin by calculating base filename.
            basename = os.path.basename(path)

            # Separate filename and extension
            (filename, ext) = os.path.splitext(basename)

            # Loop all files that start with the same base filename
            # and end in the same extension (e.g. theme1.css -> theme1*css)
            for f in [s for s in os.listdir( os.path.dirname(path) ) if (s != basename and s[0 : len(filename)] == filename and s[ -len(ext) : ] == ext)]:

                # Load "mod's" selectors using full path
                self.load_selectors_from_file(
                    os.path.join( os.path.dirname(path), f )
                )

    # Special sorting function for sorting selector matches by specificity and then by order of appearance
    def two_column_sort(self, a, b):

        # Same specificity?
        if ( a[0] == b[0] ):

            # Judge by order of appearance
            return cmp( a[1], b[1] )

        # Otherwise
        else:

            # Judge by specificity
            return cmp( a[0], b[0] )


    # Find all selectors that match a given selector bloodline
    def get_properties(self, bloodline):

        self.debug_count += 1

        #print "(#%d):  Checking bloodline:  %s" % (self.debug_count, bloodline)
        #a = time.time()

        # Store the results here, ultimately...
        #properties = {}


        debug = False
        #if ( bloodline.find(".z") >= 0 ):
        #    debug = True



        #debug = bloodline.endswith(".z")

        #if (debug):
        #    log2( "Checking bloodline:  '%s'" % bloodline )


        # Check the cache
        properties = self.get_cached_selector_properties(bloodline)

        # Found it cached?
        if (properties != None):

            # That was easy...
            return properties


        # Nope... we're going to have to do this the hard way
        else:

            # Default to no properties
            properties = {}


            matches = self.get_selector_matches_for_bloodline(bloodline)



            #print "======================="


            # Now we have to sort the matches first by specificity and then by order (for tiebreakers)
            matches.sort( self.two_column_sort )


            if (debug):
                log2( "Matches in order of specificity:" )
                for i in range( 0, len(matches) ):
                    selector = matches[i][2]
                    logn( "css", selector )
                    for key in self.properties_by_selector[selector]:
                        logn( "css", "\t%s: %s" % (key, self.properties_by_selector[selector][key]) )


            if (debug):
                log2( "\t\t*****", bloodline )

            # Now we can loop through the matches, taking properties as we go
            for i in range( 0, len(matches) ):

                # We need the selector (to read in the necessary properties) and the match type (to decide whether or not to cascade some properties)
                (selector, match_type) = (matches[i][2], matches[i][3])

                if (debug):
                    log( "\t\t", (selector, match_type) )

                # Loop through all properties
                for key in self.properties_by_selector[selector]:

                    # Perfect matches always get assigned
                    if (match_type == MATCH_PERFECT):

                        # Special case for bbcode... hacky
                        if (key == "bbcode"):

                            # Establish default, empty hash, if/a
                            if ( not (key in properties) ):

                                properties[key] = {}

                            # Then, update with the given bbcodes
                            properties[key].update(
                                self.properties_by_selector[selector][key]
                            )


                        # All other properties are single-value properties
                        else:

                            properties[key] = self.properties_by_selector[selector][key]


                        # Check for relationship overrides (e.g. padding sends its value to padding-top and padding-bottom)
                        if ( key in ATTRIBUTE_RELATIONS ):

                            for related_key in ATTRIBUTE_RELATIONS[key]:

                                properties[related_key] = self.properties_by_selector[selector][key]

                    # Inherited matches might get assigned...
                    elif (match_type == MATCH_INHERITED):

                        # ... but only if they're not on the blacklist
                        if ( not (key in NONCASCADING_ATTRIBUTES) ):

                            # Special case for bbcode... hacky
                            if (key == "bbcode"):

                                # Establish default, empty hash, if/a
                                if ( not (key in properties) ):

                                    properties[key] = {}

                                # Then, update with the given bbcodes
                                properties[key].update(
                                    self.properties_by_selector[selector][key]
                                )

                            # All other properties are single-value properties
                            else:

                                properties[key] = self.properties_by_selector[selector][key]


                            # Check for relationship overrides (e.g. padding sends its value to padding-top and padding-bottom)
                            if ( key in ATTRIBUTE_RELATIONS ):

                                for related_key in ATTRIBUTE_RELATIONS[key]:

                                    properties[related_key] = self.properties_by_selector[selector][key]


            #print "Processed bloodline in %s seconds" % (time.time() - a)
            #a = time.time()


            # Cache the properties for next time
            self.cache_selector_properties(bloodline, properties)


            if (0 and debug):
                if ( "bbcode" in properties ):
                    log( "**Final css properties, bbcode:" )
                    log( "**Selector:  %s" % bloodline )
                    for key in properties["bbcode"]:
                        log( "\t%s = %s" % (key, properties["bbcode"][key]) )
                log( "" )



            if ( bloodline == "stack.pause-menu:active>rowmenu.skills>rowmenu-group>container.option>stack.frame>container>label.debug1" ):

                if ( properties["bbcode"]["title"] == (207, 106, 19) ):
                    log( 5/0 )

                else:
                    log( "color[title] = ", properties["bbcode"]["title"] )


            # Return the properties
            return properties

    """
    rowmenu
    rowmenu > rowmenu-group
    rowmenu > rowmenu-group > label
    """


    # Find all of the defined selectors that match a given bloodline.
    # Returns a tuple with specificity data, match type, etc.
    def get_selector_matches_for_bloodline(self, bloodline):

        # Track matches
        matches = []


        #for selector in self.selector_order:
        for i in range( 0, len(self.selector_order) ):

            selector = self.selector_order[i]

            match_type = self.selector_matches_bloodline(selector, bloodline)

            # No match?  Skip...
            if (match_type == MATCH_NONE):

                #print "Testing against selector:  '%s'" % selector, " [ ]"
                pass

            # Otherwise, append while noting the match type...
            else:

                matches.append(
                    (self.compute_specificity_rating_for_selector(selector), i, selector, match_type)
                )

                if (0 and debug):
                    if (match_type == MATCH_PERFECT):
                        log2( "\tTesting against selector:  '%s'" % selector, " [x]" )
                    else:
                        log2( "\tTesting against selector:  '%s'" % selector, " [.]" )


        # Return matches
        return matches


    # Evaluate whether or not a defined selector matches against a given bloodline
    def selector_matches_bloodline(self, selector, bloodline):

        # Split the selector string into individual selectors (e.g. rowmenu rowmenu-group -> (rowmenu, rowmenu-group)
        selector_pieces = selector.split(" ")

        # Do the same with the bloodline string; this string is a complete path, a > b > c...
        bloodline_pieces = bloodline.split(">")


        # Start at the base of the selector path and travel forward.  We must find each component
        # of the selector path /somewhere/ in the bloodline (in the proper sequence, of course)...
        selector_pos = 0

        # Trace along the bloodline path; we can skip along as we need to.
        bloodline_pos = 0


        # Match the entire selector trace
        while ( ( selector_pos < len(selector_pieces) ) and ( bloodline_pos < len(bloodline_pieces) ) ):

            # If we have a match between the cursor position of both traces, we can advance the selector trace cursor
            if ( self.selectors_match( selector_pieces[selector_pos], bloodline_pieces[bloodline_pos] ) ):

                # Carry on, solider
                selector_pos += 1

                # If we just matched the final selector component (i.e. we'd end up breaking the for loop anyway),
                # then let's go ahead and return success
                if ( selector_pos >= len(selector_pieces) ):

                    # If the final bloodline piece is equal to the final selector piece (e.g. selector A B matches bloodline X > Y > A > B, A > B > A > B, etc.),
                    # then we have a perfect match (not at all reliant upon inheritance)
                    if ( self.selectors_match( selector_pieces[-1], bloodline_pieces[-1] ) ):

                        return MATCH_PERFECT

                    # Otherwise, the selector itself still applies to the bloodline via inheritance.
                    # However, certain attributes (margins, for instance) will not cascade.
                    else:

                        return MATCH_INHERITED


            # Otherwise, not much to do...
            else:
                pass


            # Always try to advance farther down the bloodline
            bloodline_pos += 1


        # If we had to break the while loop before returning success, then we couldn't match these selectors
        return MATCH_NONE


    # Evaluate whether a given selector component (e.g. label, rowmenu.someclass, etc.)
    # matches against a given bloodline component (e.g. label.this-matches, rowmenu.this-does-not, etc.)
    # We use a function for this to account for wildcards...
    # If raw_selectors is set to True, then we skip class / state processing
    def selectors_match(self, selector_component, bloodline_component, raw_selectors = False):

        # Quick check for perfect match
        if (selector_component == bloodline_component):

            return True

        # Wildcards match everything
        elif ( (selector_component in ("*", "$") ) or (bloodline_component == "*") ):

            return True

        # We can still win, perhaps, but now we need to check for classes and such...
        elif (not raw_selectors):

            # Split selector component into widget, class
            (selector_base, selector_class, selector_state) = self.separate_selector_into_base_class_and_state(selector_component)

            # Same for the bloodline
            try:
                (bloodline_base, bloodline_class, bloodline_state) = self.separate_selector_into_base_class_and_state(bloodline_component)
            except:
                logn( "css", "sel:  '%s'" % bloodline_component )
                logn( "css", "aborting!" )
                sys.exit()


            # If selector has no base, we'll compare only class and state
            if (selector_base == ""):

                # If selector has no state, then it's a straight-up class check
                if (not selector_state):

                    return (selector_class == bloodline_class)

                # Otherwise, both class and state must match
                else:

                    return ( (selector_class == bloodline_class) and (selector_state == bloodline_state) )


            # If the selector component has a base only (no class), then bloodline class means nothing
            elif (not selector_class):

                # If selector has no state, then state means nothing
                if (not selector_state):

                    # Just check the bases
                    return ( self.selectors_match(selector_base, bloodline_base, raw_selectors = True) )

                # Otherwise, state must still match
                else:

                    return ( ( self.selectors_match(selector_base, bloodline_base, raw_selectors = True) ) and (selector_state == bloodline_state) )


            # If the selector has a base and a class, we've gotta check both
            else:

                # If the selector doesn't specify a state, we do a simple comparison...
                if (not selector_state):

                    # The base and the class must both match
                    return ( ( self.selectors_match(selector_base, bloodline_base, raw_selectors = True) ) and (selector_class == bloodline_class) )

                # Otherwise, everything must match!
                else:

                    return ( ( self.selectors_match(selector_base, bloodline_base, raw_selectors = True) ) and (selector_class == bloodline_class) and (selector_state == bloodline_state) )


    # Split a given selector into base / class / state
    def separate_selector_into_base_class_and_state(self, selector):

        # Does it even contain a class?
        if ( selector.find(".") >= 0 ):

            # Does it contain a state, as well?
            if ( selector.find(":") >= 0 ):

                # Do we have a base in this selector?
                if ( not selector.startswith(".") ):

                    # Return base, class, and state...
                    return re.findall( "[^\.\:]+", selector )

                # If not, we have to do this a little differently...
                else:

                    # Let's strip the leading period, then split it into class/state
                    (css_class, css_state) = selector.lstrip(".").split(":")

                    # Return empty base
                    return ("", css_class, css_state)

            # Otherwise, only base and class...
            else:

                (base, css_class) = selector.split(".", 1)

                return (base, css_class, None)

        # If not, we return the raw selector and no class
        else:

            # No class, but perhaps a state?
            if ( selector.find(":") >= 0 ):

                # Get base and state
                (base, css_state) = selector.split(":", 1)

                return (base, None, css_state)

            # Only a base, no class and no state
            else:

                return (selector, None, None)


    # Compute a given selector's specificity rating
    def compute_specificity_rating_for_selector(self, selector):

        # Start from the beginning
        rating = 0


        # Separate selector into components
        pieces = selector.split(" ")

        # Trace
        for piece in pieces:

            # Selector with a class weighs more
            if ( piece.find(".") >= 0 ):

                rating += 100

            # If it has some state attribute (e.g. :active), we give it a few points...
            elif ( piece.find(":") >= 0 ):

                rating += 10

            # Otherwise, base score...
            else:

                # Except for wildcards, which get 0 points
                if ( piece == "*" ):

                    rating += 0 # :)

                # Wildcard dollar signs earn a 100000 point bonus.  This is, of course, not at all real CSS.
                elif ( piece == "$" ):

                    rating += 100000 # Kind of like applying "!important" to every property within the selector, in theory...

                else:

                    rating += 1


        return rating
