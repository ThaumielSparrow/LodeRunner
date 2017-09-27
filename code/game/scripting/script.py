import sys

import re
import copy

import objects

from code.utils.common import log, log2, logn

from code.constants.scripting import *


# Local debug flag.
# When I release this game, I will either remove or comment out all DEBUG-related code, just as an optimization.
DEBUG = False

# Local error handling function.
# Expects a string representing the error message.
def handle_error(s):

    if ( "--debug" in sys.argv ):

        # Add to file
        f = open("integrity1.txt", "a")
        f.write( "%s\n\n" % s )
        f.close()

    # Let's print to console as well
    log2(s)


class Script:

    def __init__(self, s):

        # Statements within this script
        self.statements = self.parse(s)

        # Sometimes we will exit a script in the midst of processing it,
        # essentially "pausing" the script.  Track the position as we run each statement.
        self.cursor = 0


    # debug
    def dump(self, prefix = ""):

        for statement in self.statements:
            statement.dump(prefix)


    # Restart a script (set cursor to 0)
    def reset(self):

        # Set cursor to 0
        self.cursor = 0

        # Reset each statement
        for statement in self.statements:

            # This primarily aims to reset conditional subscripts (i.e. nested Script objects)
            statement.reset()


    # Parse a given block of script data.
    # Returns a series of individual statements (of any number of links) that make up the script.
    def parse(self, s):

        #print s
        #for (name, value) in placeholders:
        #    print (name, value)

        # Before anything else, let's remove all code comments
        s = re.sub(
            "//.*?\n",
            "",
            s
        )

        # Comments might end a script (no newline after)
        s = re.sub(
            "//.*?$",
            "",
            s
        ).strip()


        # Next, search for defined aliases
        aliases = re.findall(
            "#define ([\S]+) (.*?)\n",
            s
        )

        # Sort in reverse alphabetical order.  This ensures that I replace longer aliases
        # before I replace shorter aliases, meaning that if one alias is the same as another alias with extra characters,
        # I don't greedily replace a portion of the longer alias with the shorter alias and thus corrupt the longer alias.  Somewhat hacky, probably.
        aliases.sort()
        aliases.reverse()

        # Remove defined aliases; we don't want to actually process them in any way.
        s = re.sub(
            "#define .*?\n",
            "",
            s
        )


        # Before we strip out all whitespace and periods, we
        # extract all string data (parameters) and replace them with placeholders,
        # in case those strings have whitespace and periods in them.
        placeholders = []

        # Pass placeholders list by reference, of course
        s = replace_delimited_strings_and_save_placeholders('"', '"', s.strip(), placeholders, "string")


        # Back to the #define stuff:  let's replace all alias references with the provided translation for each one
        for (alias, translation) in aliases:

            logn( "script debug", ("alias", alias, translation) )

            # Replace all
            s = s.replace(alias, translation)


        # It's quite possible that some aliases introduced more string literals.
        # We'll add placeholders for each of those as well now.
        s = replace_delimited_strings_and_save_placeholders('"', '"', s.strip(), placeholders, "string")


        # Remove multi-spaced lines
        s = re.sub(
            "[\n]+",
            "\n",
            s
        )

        # Any line ending in a period implies that the next line continues its statement / logic
        s = re.sub(
            "\.\n",
            ".",
            s
        )

        # Same logic applies for a string ending in a comma
        s = re.sub(
            ",\n",
            ",",
            s
        )

        # Same logic applies for a string ending in a (
        s = re.sub(
            "\(\n",
            "(",
            s
        )

        # If the next line were to begin with a closing parentheses, it must belong to the previous line
        s = re.sub(
            "\n\)",
            ")",
            s
        )

        # Now let's remove all extra whitespace from the string.
        s = re.sub(
            "[\t\n]",
            "",
            s
        )
        s = re.sub(
            "[ ]+",
            " ",
            s
        )


        # With strings replaced with placeholders, we can safely remove any whitespace that follows a comma.
        # This helps to simplify parsing of conditional statements.
        s = re.sub(
            ",[\s]*",
            ",",
            s
        )


        # For any "else" statement, we'll add an implicit ():  else{...} -> else(){}.
        # This is a hack that simplifies parsing for me.
        #s = s.replace("}else{", "}else(){")
        s = re.sub(
            "}[\s]*else[\s]*{",
            "} else(1) {",          # (1) will always evaluate to True.
            s
        )


        logn( "script debug", "Parsed Data:\n%s" % s )



        # A second list to store parameter placeholders.  Note that we don't run this
        # logic until we've previously added placeholders for string constants (and also, we have removed all unnecessary formatting characters).
        placeholders2 = []
        s = replace_delimited_strings_and_save_placeholders('(', ')', s, placeholders2, "params")

        placeholders3 = []
        s = replace_delimited_strings_and_save_placeholders('{', '}', s, placeholders3, "subscript", inclusive = True, suffix = ";")


        # Now we have ensured that each statement / condition has a semicolon
        # at its end.  Here, we'll split by semicolon to get each distinct statement / condition.
        lines = s.split(";")

        """
        for (name, value) in placeholders3:
            logn( "script debug", (name, value) )

        for (name, value) in placeholders2:
            logn( "script debug", (name, value) )

        for (name, value) in placeholders:
            logn( "script debug", (name, value) )
        """


        for i in range( 0, len(lines) ):

            for (name, value) in placeholders3:

                lines[i] = lines[i].replace(name, value)

            for (name, value) in placeholders2:

                lines[i] = lines[i].replace(name, value)

            for (name, value) in placeholders:

                lines[i] = lines[i].replace(name, value)

            logn( "script debug", lines[i] )


        for line in lines:
            logn( "script debug", "Script Line:  %s" % line )



        statements = []

        # Loop through all lines
        for line in lines:

            if ( len( line.strip() ) > 0 ):

                statements.append(
                    parse_expression(line)
                )


        return statements


    # Run this script
    def run(self, control_center, universe, base = None):

        # Loop through script
        while ( self.cursor < len(self.statements) ):

            # Attempt to run the statement.
            result = self.statements[self.cursor].evaluate(control_center, universe, base = base)

            logn( "script debug", "result:  %s" % result )

            # If the result is "pending," then we'll try this statement again next time
            # we run the script.
            if (result == EXECUTE_RESULT_PENDING):

                # Check to see if we have "simultaneous" statements following this one...
                cursor2 = (self.cursor + 1)

                # Loop through any simultaneous statement
                while ( ( cursor2 < len(self.statements) ) and ( self.statements[cursor2].is_simultaneous() ) ):

                    # Execute the statement.  We don't care about its execution result (because we're still on the one that is pending).
                    # Note that we'll run this statement at least one more time (as the cursor advances in its usual fashion).
                    self.statements[cursor2].evaluate(control_center, universe, base = base)

                    # Advance temporary cursor
                    cursor2 += 1


                return False

            # If the statement contained a condition that evaluated to true,
            # then we'll want to skip over any subsequent elif/else statements.
            elif (result == CONDITION_MET):

                # Advance to the next line
                self.cursor += 1

                # Keep peeking ahead to the next line, seeing if we should skip it.
                while ( (self.cursor < len(self.statements)) and ( self.statements[self.cursor].links[0].method in ("elif", "else") ) ):

                    # Move forward one line, essentially skipping the elif/else blocks.
                    self.cursor += 1
                    logn( "script debug", "Skipping statement %d" % (self.cursor + 1) )

            # If the statement contained a condition that evaluated to true but did NOT
            # finish its subscript execution, then we will try this line again next time,
            # once again entering the subscript in an attempt to finish it.
            elif (result == CONDITION_MET_BUT_PENDING):

                # Do not advance the cursor at all.
                # Return from the script, incomplete.
                return False

            # If the statement containd a condition that did not evaluate to true,
            # we will continue to the next line with no other action.
            elif (result == CONDITION_NOT_MET):

                self.cursor += 1

            # For any other result, we will continue on to the next line
            else:

                self.cursor += 1


        # We finished executing the script
        return True

        # Cycle through each statement
        #for i in range( 0, len(self.statements) ):

        #    print "Evaluating statement %d" % (i + 1)
        #    print self.statements[i].evaluatecontrol_center, universe)


class Statement:

    def __init__(self):

        # Links within this statement
        self.links = []

        # How many times have we run this statement?
        # Generally, we'll run single-use statements, declarations, conditions, etc.
        # Sometime statements, though (e.g. sleep, planar slide, etc.) will run for more than one frame.
        self.frames = 0

    # debug
    def dump(self, prefix = ""):

        logn( "script dump", "%sLinks:" % prefix )

        #print self
        for link in self.links:

            if (link.type == LINK_TYPE_METHOD):

                logn( "script dump", "%s\tMethod/Property:  %s\n%s\tType:  %s\n" % (prefix, link.method, prefix, "Method") )
                logn( "script dump", "%s\tParameters:" % prefix )

                for p in link.parameters:
                    p.dump(prefix + "\t")

                logn( "script dump", "%s\tSubscript:" % prefix )
                logn( "script dump", "%s\t\t%s" % (prefix, link.subscript) )

            elif (link.type == LINK_TYPE_CONDITIONAL):

                logn( "script dump", "%s\tMethod/Property:  %s\n%s\tType:  %s\n" % (prefix, link.method, prefix, "Conditional") )
                logn( "script dump", "%s\t\"Parameters\":" % prefix )

                for p in link.parameters:
                    p.dump(prefix + "\t")

                logn( "script dump", "%s\tCondition:" % prefix )
                logn( "script dump", "%s\t\t%s" % (prefix, link.condition) )
                logn( "script dump", "%s\tSubscript:" % prefix )
                link.subscript.dump()

            elif (link.type == LINK_TYPE_CONSTANT):

                logn( "script dump", "%s\tMethod/Property:  %s\n%s\tType:  %s\n" % (prefix, link.method, prefix, "Constant") )

            elif (link.type == LINK_TYPE_OBJECT):

                logn( "script dump", "%s\tMethod/Property:  %s\n%s\tType:  %s\n" % (prefix, eval(link.method), prefix, "Object") )


    # Reset all links
    def reset(self):

        # Reset frames count, we're running it from the start again
        self.frames = 0


        # Loop links
        for link in self.links:

            # Reset link
            link.reset()


    # Add a new link to this statement
    def add_link(self, link):

        # Add
        self.links.append(link)

        # Return new link
        return self.links[-1]


    # Check to see if this is a "simultaneous" statement
    def is_simultaneous(self):

        # Sanity
        if ( len(self.links) > 0 ):

            # Does the first link start with a plus sign?
            return self.links[0].method.startswith("+")


        return False


    # Evaluate this statement (evaluate each link)
    def evaluate(self, control_center, universe, base = None):

        # Quickly count this evaluation
        self.frames += 1


        # A statement without a link will do nothing
        if ( len(self.links) == 0 ):

            # Abort
            return None

        else:

            # If the first link is a method, then we will begin evaluating the
            # method chain.
            if (self.links[0].type == LINK_TYPE_METHOD):

                # I don't know if this is the best idea.  I want to include a Sleep()
                # call, and it's kind of like a system event, so I'll add in a special check
                # for it here.
                if ( self.links[0].method == "sleep" ):

                    # See if we've slept for long enough yet...
                    if ( self.frames > int( self.links[0].parameters[0].evaluate(control_center, universe, base = None) ) ):

                        # Done
                        return EXECUTE_RESULT_DONE

                    # Otherwise, we must continue sleeping
                    else:

                        # Sleep...
                        return EXECUTE_RESULT_PENDING

                # Evaluate all other methods via the object query scripting system
                else:

                    # A brutal hack to get frame count to each link **HACK
                    universe.get_session_variable("tmp.link.frames").set_value("%d" % self.frames)


                    # Evaluate first link as a "Base" queryobject
                    result = objects.Base().evaluate(
                        self.links[0].method.lstrip("+"), # Strip off the plus sign, which indicates a "simultaneous" statement
                        self.links[0].parameters,
                        control_center,
                        universe
                    )
                    logn( "script debug", "Result:  %s" % result )

                    # Prepare to move to the 2nd link in the chain, if/a.
                    i = 1

                    # As long as the first method returned a query object, let's begin stepping through each link in the method chain.
                    while ( (result != None) and (i < len(self.links)) and (self.links[i].type == LINK_TYPE_METHOD) ):

                        # Evaluate the next chain link
                        result = result.evaluate(
                            self.links[i].method,
                            self.links[i].parameters,
                            control_center,
                            universe
                        )
                        logn( "script debug", "Result:  %s" % result )

                        # Always attempt to continue to the next link
                        i += 1

                    return result

            # The "this" keyword will function just as an ordinary method would, except that we'll use
            # the specified "base" object instead of instantiating objects.Base()
            elif (self.links[0].type == LINK_TYPE_THIS):

                # A brutal hack to get frame count to each link **HACK
                universe.get_session_variable("tmp.link.frames").set_value("%d" % self.frames)

                # Use the given base object
                result = base


                # Prepare to move to the 2nd link in the chain, if/a.
                i = 1

                # As long as the first method returned a query object, let's begin stepping through each link in the method chain.
                while ( (result != None) and (i < len(self.links)) and (self.links[i].type == LINK_TYPE_METHOD) ):

                    # Evaluate the next chain link
                    result = result.evaluate(
                        self.links[i].method,
                        self.links[i].parameters,
                        control_center,
                        universe
                    )

                    # Always attempt to continue to the next link
                    i += 1

                return result

            # If the first link is a conditional, then we simply evaluate the conditional.
            # If the conditional evaluates to true, then it will implicitly execute its subscript data.
            elif (self.links[0].type == LINK_TYPE_CONDITIONAL):

                return self.links[0].evaluate(control_center, universe, base = base)

            # If the first link is an iterator, we loop through all of the iterable items and
            # return whether or not hall have evaluated to True
            elif (self.links[0].type == LINK_TYPE_ITERATOR):

                return self.links[0].evaluate(control_center, universe, base = base)

            # Any other link type (e.g. string constant, object) will return as its core type
            else:

                return self.links[0].evaluate(control_center, universe, base = base)


class StatementLink:

    def __init__(self, link_type, method, parameter_statements = [], condition = "", subscript = None):

        # Link type
        self.type = link_type

        # Method / property for this link
        self.method = method

        # Parameters for this link
        self.parameters = parameter_statements

        # Conditional links will retain the conditional script (with placeholders)
        self.condition = condition

        # Conditional links will only evaluate on the first run.
        # Thereafter, they will use a cached result.
        self.cached_condition_result = None

        # Subscript data (e.g. script code to run for conditionals)
        self.subscript = subscript


        # Iterator links will need a place to store a unique Script for each match.
        # Currently we must wait until runtime to populate this hash.
        self.iterator_matches = None


        # A range() interator needs to know its bounds
        self.iterator_range = (0, 0)                        # A pair of Statements
        self.evaluated_iterator_range = (0, 0)              # A pair of evaluated Statements

        # The range() iterator needs to know how many times it's performed its action
        # When set to None, we will evaluate the given iterator range Statements and set this cursor to the starting value
        self.iterator_cursor = None


    # Reset this link
    def reset(self):

        # Reset cached condition result
        self.cached_condition_result = None


        # If we have a subscript (i.e. Script object), let's reset it
        if (self.type == LINK_TYPE_CONDITIONAL):

            # Check for a sub-Script object
            if (self.subscript):

                # Reset
                self.subscript.reset()

        # Reset all iterator data, if necessary
        elif (self.type == LINK_TYPE_ITERATOR):

            # Throw away existing match data
            self.iterator_matches = None

            # Reset iterator cursor, for range() iterators
            self.iterator_cursor = None


    # Evaluate the return value of this link statement.
    def evaluate(self, control_center, universe, base = None):

        # String constant?
        if (self.type == LINK_TYPE_CONSTANT):

            logn( "script debug", "EVALUATING:  LINK_TYPE_CONSTANT" )
            logn( "script debug", "Value:  %s" % self.method )

            # We store the value in the "method" property.  Lame, I know.
            return self.method.strip('"')

        # Object (e.g. hash)?
        elif (self.type == LINK_TYPE_OBJECT):

            # Same lame way of storing it in the method property.
            # eval() to convert it to a hash object.
            return eval(self.method)

        # Conditional
        elif (self.type == LINK_TYPE_CONDITIONAL):

            # Check for cached condition evaluation
            condition_evaluates_to_true = self.cached_condition_result

            # Do we need to evaluate this as a fresh condition?
            if (condition_evaluates_to_true == None):

                # First, replace each placeholder in the conditional expression
                # with the evaluated placeholders.
                condition = self.condition

                logn( "script debug", "Conditional:  ", condition )

                # Replace all "parameters," each of which is a statement that forms a part of the conditional expression.
                for i in range( 0, len(self.parameters) ):

                    # Evaluate the return value of this part of the conditional expression.
                    evaluation = self.parameters[i].evaluate(control_center, universe, base = base)

                    # Validate that we got some evaluation back
                    if (evaluation):

                        # Replace the placeholder with the return value
                        condition = condition.replace(
                            "@^statement%d$@" % (i + 1),
                            "%s" % self.parameters[i].evaluate(control_center, universe, base = base)
                        )

                    # Otherwise, throw a 0 in there.  (?)
                    else:

                        condition = condition.replace(
                            "@^statement%d$@" % (i + 1),
                            "0"
                        )

                logn( "script debug", "Conditional resolution:  ", condition )


                # Evaluate and cache
                condition_evaluates_to_true = False


                # Assume
                result = False

                # Try to evaluate
                try:
                    result = eval(condition)

                # Record error
                except:

                    """ DEBUG check """
                    if (DEBUG):

                        # Save error
                        handle_error( "Eval error:  %s" % condition )
                    """ End DEBUG """


                if (result):
                    condition_evaluates_to_true = True


                # Cache
                self.cached_condition_result = condition_evaluates_to_true


            # If we successfully evaluate the conditional expression, then
            # we subsequently run the associated subscript.
            if (condition_evaluates_to_true):

                #print "Yo:  Condition worked:  %s" % condition

                #self.subscript.dump()
                result = self.subscript.run(control_center, universe)

                if (result):

                    return CONDITION_MET

                else:

                    return CONDITION_MET_BUT_PENDING

            else:

                #print "Yo:  Condition failed:  %s" % condition

                """ In DEBUG mode, we process all conditional subscripts, just to check the validity of
                    each of the calls within the subscript. """
                if (DEBUG):

                    # ...
                    result = self.subscript.run(control_center, universe)

                    if (result):

                        return CONDITION_MET

                    else:

                        return CONDITION_MET_BUT_PENDING


                else:
                    return CONDITION_NOT_MET
                """ END DEBUG / NON-DEBUG"""

        # The each() iterator
        elif (self.type == LINK_TYPE_ITERATOR):

            # each() iterator
            if (self.method == "each"):

                # If we haven't yet created a unique Script object for each matched result, then let's evaluate
                # the matched result Statement and create that Script for each match.
                if (self.iterator_matches == None):

                    # Create an empty hash of Script objects; we'll want to run a unique Script object for each iterated object
                    self.iterator_matches = {}

                    # Loop through our results, creating a Script object for each one (key by object handle)
                    for handle in self.parameters.evaluate(control_center, universe).handles:

                        # Create unique Script
                        self.iterator_matches[handle] = copy.deepcopy(self.subscript)


                # We're going to borrow the condition met-but-pending logic here.  For starters,
                # assume all of the iterated elements have finished their scripts.
                result = CONDITION_MET
                logn( "script debug", "iterator matches:  ", self.iterator_matches )

                # Loop through each item's, keyed by the query result handle.
                # Remember that we assigned a hash to the .subscript attribute for the iterator.
                for handle in self.iterator_matches:

                    # Check local result
                    handle_result = self.iterator_matches[handle].run(control_center, universe, base = handle)

                    # if any of the iterated items does not finish, we must continue looping next time
                    if (not handle_result):

                        # All must complete
                        result = CONDITION_MET_BUT_PENDING

                # Return overall result
                return result

            # range() iterator
            elif (self.method == "range"):

                # Scope
                result = None

                # Do we need to evaluate the given range Statement expressions?
                if (self.iterator_cursor == None):

                    # Evaluate
                    self.evaluated_iterator_range = (
                        int( self.iterator_range[0].evaluate(control_center, universe) ),
                        int( self.iterator_range[1].evaluate(control_center, universe) )
                    )

                    # Start the cursor at the beginning
                    self.iterator_cursor = self.evaluated_iterator_range[0]


                # We're going to try to run every iteration in one pass, if we can
                looping = True

                # Loop
                while (looping):

                    # Must we continue looping?
                    if ( self.iterator_cursor < self.evaluated_iterator_range[1] ):

                        # Run subscript
                        local_result = self.subscript.run(control_center, universe, base = None)

                        # If it finished, then let's reset the subscript (for another potential loop) and increment the range cursor
                        if (local_result):

                            # Reset for another round
                            self.subscript.reset()

                            # Increment cursor
                            self.iterator_cursor += 1

                        # If we couldn't finish running the subscript during this iteration,
                        # we'll have to abandon the loop and resume next time...
                        else:

                            # Abandon loop
                            looping = False

                    # Done looping
                    else:

                        # Abandon loop
                        looping = False


                # Have we completed the range?
                if ( self.iterator_cursor >= self.evaluated_iterator_range[1] ):

                    # Done
                    return CONDITION_MET

                # No
                else:

                    # We'll have to continue this next time
                    return CONDITION_MET_BUT_PENDING

def parse_expression(line):
    prefix = ""

    # Create new statement object
    statement = Statement()

    if ( line.strip() == "" ):
        return statement

    # Save all statement links we find within this expression
    results = []


    logn( "script debug", "line before:  %s" % line.strip() )

    #print 1, line

    placeholder_strings = []
    line = replace_delimited_strings_and_save_placeholders('"', '"', line.strip(), placeholder_strings, "string")

    #print 2, line

    placeholder_objects = []
    line = replace_delimited_strings_and_save_placeholders('{', '}', line, placeholder_objects, "object")

    #print 3, line

    placeholder_params = []
    line = replace_delimited_strings_and_save_placeholders('(', ')', line, placeholder_params, "param")



    # Now that we've moved all statements onto a single line
    # and removed whitespace, let's split the line by period to
    # get each and every link in the statement's chain.
    links = line.split(".")

    #print "links:  ", links
    logn( "script debug", "line after:  %s" % line )

    # Let's move through each link and re-insert
    # the placeholder string data.  We won't be splitting individual links any further, so we'll do this now.
    for i in range( 0, len(links) ):

        # Now that we've split the expression into distinci links,
        # we can safely restore the parameter placeholders.
        for (name, value) in placeholder_params:

            # Restore
            links[i] = links[i].replace(name, value)

        # Check all placeholders
        #for (name, value) in placeholder_strings + placeholder_objects:

        #    # Attempt replace
        #    links[i] = links[i].replace(name, value)




        # Track property / function call
        method = None

        # Track parameter expressions.
        parameters = []

        parameter_statements = []

        # Before we can evaluate the parameters, we must once again replace string constants with placeholders.
        # Note that this is the only placeholder logic we will do in this block.
        #parameter_placeholder_strings = []
        #parameter_placeholder_objects = []

        #links[i] = replace_delimited_strings_and_save_placeholders('"', '"', links[i], parameter_placeholder_strings, "string")

        # Ok, we also want to add placeholders for any hash parameters
        #links[i] = replace_delimited_strings_and_save_placeholders('{', '}', links[i], parameter_placeholder_objects, "object")


        # Let's calculate the parameters sent to this link.
        # First, find the opening parenthesis.
        pos = links[i].find("(")

        # Do we have a parameter section?
        if (pos >= 0):

            # Grab the method
            method = links[i][0 : pos].strip()

            # Find the end of the parameter section
            end = links[i].find(")", pos + 1)

            # Ensure balanced parentheses (i.e. skip over nested parentheticals)
            while ( (end > pos) and ( len(links[i][pos + 1 : end].replace("(", "")) != len(links[i][pos + 1 : end].replace(")", "")) ) ):

                # Search again
                end = links[i].find(")", end + 1)


            # If we didn't find an end to the parameter section, pass
            if (end < 0):

                logn( "script debug", "Aborting:  cannot find an end to the parameter list:  %s" % links[i] )
                sys.exit()

            else:

                # Extract parameter data
                parameter_string = links[i][pos + 1 : end]
                logn( "script debug", "parameter_string = ", parameter_string )


                # Having found the end of the parameters section, we can safely restore
                # placeholder data for the remaining portion of the string (i.e. subscript data).
                s2 = links[i][ (end + 1) : len(links[i]) ]

                # Loop object placeholders
                for (name, value) in placeholder_objects:

                    # Restore for the end of the string
                    s2 = s2.replace(name, value)

                # Loop string placeholders
                for (name, value) in placeholder_strings:

                    # Restore for the end of the string
                    s2 = s2.replace(name, value)


                # Update link data
                links[i] = links[i][0 : (end + 1)] + s2


                # Before handling the parameter data, I want to also check for any subscript data,
                # namely the "do this" code block for if/elif/else statements and each() iterators.
                # I begin the search after the end of the parameter data.
                pos2 = links[i].find("{", end + 1)

                # Find the end of the subscript section
                end2 = links[i].find("}", pos2 + 1)

                # Ensure balanced parentheses (i.e. skip over nested parentheticals)
                while ( (end2 > pos2) and ( len(links[i][pos2 + 1 : end2].replace("{", "")) != len(links[i][pos2 + 1 : end2].replace("}", "")) ) ):

                    # Search again
                    end2 = links[i].find("}", end2 + 1)


                # Default, assume no subscript data.
                subscript_string = ""

                # Did we find a subscript section?
                if (end2 >= 0):

                    # Read subscript data
                    subscript_string = links[i][pos2 + 1: end2]
                    #print subscript_string


                # Did we find a conditional expression?
                if ( method in ("if", "elif", "else") ):

                    logn( "script debug", "Conditional statement:  '%s'" % parameter_string )

                    # We need to find all statements within the conditional expression,
                    # parse them into statement objects, and then insert placeholders into the original conditional expression.
                    # When we run the script live, we'll evaluate each statement, place the returned value into the placeholder, and
                    # finally do an eval() on the resultant string.
                    parameters = []

                    # Find the first script statement within the conditional expression
                    pos = -1
                    if ( re.search("[\w]+?\(", parameter_string) ):
                        pos = re.search("[\w]+?\(", parameter_string).start()

                    offset = 0

                    # Loop all script statements, eventually
                    while (pos >= 0):

                        logn( "script debug", "Match:  ", parameter_string[offset + pos : offset+pos+10] )

                        # To find the end of the script statement, we need to find either
                        # a space, a comparison character (e.g. =, >, <, etc.), or an unbalanced (i.e. extra) closing parenthesis
                        end = pos + 1
                        looping = True

                        # Look for the end of the script statement
                        while (looping):

                            # First, if we reach the end of the parameter string, then we must implicitly end the statement as well.
                            if ( end == len( parameter_string[offset + end] ) - 1 ):

                                # Add +1 to the "end" variable so that our substring includes the final character
                                end += 1

                                # EOF, basically
                                looping = False
                                logn( "script debug", "looping c", looping )

                            # Comparison character guarantees end, as does a space
                            elif ( ( parameter_string[offset + end] in ("=", "!", "<", ">") ) or ( parameter_string[offset + end] == " " ) ):

                                # We found the end
                                looping = False
                                logn( "script debug", "looping a", looping )

                            # A closing parenthesis might indicate the end of the statement, if it's unbalanced
                            # (i.e. signals the end of a parenthetical).
                            elif ( parameter_string[offset + end] == ")" ):

                                # Check for imbalance
                                looping = ( ( len( parameter_string[offset + pos : (end + 1)].replace("(", "") ) - 1 ) != len( parameter_string[offset + pos : (end + 1)].replace(")", "") ) )

                                # If we're still looping, then we'll continue our search...
                                if (looping):
                                    end += 1
                                logn( "script debug", "looping b", looping )
                                logn( "script debug", parameter_string[offset + pos : (end + 1)] )

                            # Keep looking for the end
                            else:
                                end += 1


                        # Extract the statement phrase
                        phrase = parameter_string[offset + pos : offset + end]
                        logn( "script debug", "Found phrase:  '%s'" % phrase )
                        #print 5/0


                        # Replace objects and string constants in the phrase before parsing it
                        for (name, value) in placeholder_objects:

                            # Restore
                            phrase = phrase.replace(name, value)

                        for (name, value) in placeholder_strings:

                            # Restore
                            phrase = phrase.replace(name, value)


                        # Track it as a "parameter"
                        parameters.append( parse_expression(phrase) )

                        # Replace with placeholder
                        parameter_string = parameter_string[0 : (offset + pos)] + "@^statement%d$@" % len(parameters) + parameter_string[(offset + end) : len(parameter_string)]
                        #print parameter_string


                        # Look for another statement
                        offset = pos + 1

                        pos = -1
                        if ( re.search("[\w]+?\(", parameter_string[offset : len(parameter_string)]) ):
                            pos = re.search("[\w]+?\(", parameter_string[offset : len(parameter_string)]).start()


                    # Loop all placeholders
                    for (name, value) in placeholder_objects:

                        # Restore
                        parameter_string = parameter_string.replace(name, value)

                    for (name, value) in placeholder_strings:

                        # Restore
                        parameter_string = parameter_string.replace(name, value)


                    statement.add_link(
                        StatementLink(
                            LINK_TYPE_CONDITIONAL,
                            method,
                            parameters,
                            parameter_string,
                            Script(subscript_string)
                        )
                    )

                    logn( "script debug", subscript_string )
                    statement.links[-1].subscript.dump()
                    #print 5/0


                    """
                    # Strip off any leading parenthesis.
                    while ( 0 ):#parameter_string.startswith("(") ):

                        # Let's find the ) that closes this parenthetical and remove it as well.
                        end2 = parameter_string.find(")")

                        # Balance parentheses
                        while ( (end2 > 0) and (0) ):
                            pass
                    """

                # Did we find an each() iterator?
                elif ( method == "each" ):

                    # Replace parameter string with original default data, removing placeholders...
                    for (name, value) in placeholder_objects:

                        # Restore
                        parameter_string = parameter_string.replace(name, value)

                    for (name, value) in placeholder_strings:

                        # Restore
                        parameter_string = parameter_string.replace(name, value)

                    # The each() iterator expects only one parameter, which should be a script call
                    # that returns some sort of list-based query result.  So, let's evaluate that
                    # expression and (hack) stash the results in the "parameters" attribute.
                    parameters = parse_expression(parameter_string)

                    # Create a new link
                    statement.add_link(
                        StatementLink(
                            LINK_TYPE_ITERATOR,
                            method,
                            parameters,             # The Statement we got by parsing the single parameter.  We'll have to finish evaluating this at runtime...
                            None,                   # No conditional parameter data
                            Script(subscript_string)
                        )
                    )


                # Did we find a range() iterator?
                elif ( method == "range" ):

                    # First, let's split by comma to get the range() params (i.e. from, to)
                    pieces = parameter_string.split(",", 1)

                    # Validate that we provided both arguments
                    if ( len(pieces) == 2 ):

                        # Replace placeholders with original values
                        for j in range( 0, len(pieces) ):

                            # Loop all placeholders
                            for (name, value) in placeholder_objects:

                                # Restore
                                pieces[j] = pieces[j].replace(name, value)

                            for (name, value) in placeholder_strings:

                                # Restore
                                pieces[j] = pieces[j].replace(name, value)


                        # Read range.  The range values may be expressions.  We won't evaluate those expressions here;
                        # we have to wait until script runtime to finalize the calculations.
                        (a, b) = (
                            parse_expression( pieces[0] ),
                            parse_expression( pieces[1] )
                        )

                        # Create a new link
                        link = statement.add_link(
                            StatementLink(
                                LINK_TYPE_ITERATOR,
                                method,
                                parameters,             # The Statement we got by parsing the single parameter.  We'll have to finish evaluating this at runtime...
                                None,                   # No conditional parameter data
                                Script(subscript_string)
                            )
                        )

                        # Hack in those unevaluated range values
                        link.iterator_range = (a, b)
        

                # We found an ordinary method
                else:

                    # Do we have parameters?
                    if ( len(parameter_string) > 0 ):

                        logn( "script debug", "parse parameters:  %s" % parameter_string )

                        # Because we replaced all string constants, hashes, etc.,
                        # we can safely split by comma at this point to get the individual parameter expressions.
                        parameters.extend(
                            parameter_string.split(",")
                        )

                        # Having acquired each distinct parameter, we will now restore the original values (removing placeholders) for each piece.
                        for j in range( 0, len(parameters) ):

                            # Loop all placeholders
                            for (name, value) in placeholder_objects:

                                # Restore
                                parameters[j] = parameters[j].replace(name, value)

                            for (name, value) in placeholder_strings:

                                # Restore
                                parameters[j] = parameters[j].replace(name, value)
                            #print "parameter[%d] = " % j, parameter_string


                        for s in parameters:

                            logn( "script debug", "parse expression:  '%s'" % s )

                            parameter_statements.append(
                                parse_expression(s)
                            )

                            """
                            if (0):
                                r = parse_expression(s)
                                if ( len(r.links) > 0 ):
                                    if ( r.links[0].evaluate(None) == "xxxactive" ):
                                        logn( "script debug", s )
                                        #print 5/0
                            """


                    statement.add_link(
                        StatementLink(
                            LINK_TYPE_METHOD,
                            method,
                            parameter_statements,
                            subscript_string
                        )
                    )


                    """
                    log( "%smethod: %s" % (prefix, method) )# string = %s" % parameter_string
                    log( "%sparameters:  " % prefix, parameters )# string = %s" % parameter_string
                    log( "" )
                    for p in parameters:
                        log( "%sParameter:" % prefix, p )
                        parse_script(p)
                    log( "***" )
                    """


        # Is this link a "this" reference?
        elif ( links[i] == "this" ):

            # Add a new "this" link
            statement.add_link(
                StatementLink(
                    LINK_TYPE_THIS,
                    links[i]            # Not really used, we'll know what to do as soon as we identify the link type (LINK_TYPE_THIS)
                )
            )

        # This call must be to a property (e.g. something().length),
        # because it does not provide parameter data.
        else:

            # This link does not have any parameter data.
            # We are looking at a constant string, or perhaps an object.  Let's replace object and string constants in this link now.
            for (name, value) in placeholder_objects:

                # Restore
                links[i] = links[i].replace(name, value)

            # Replace objects first, strings second.
            for (name, value) in placeholder_strings:

                # Restore
                links[i] = links[i].replace(name, value)

            # If the string begins with an {, then we have an object (hash).
            if ( links[i][0] == "{" ):

                method = links[i]

                statement.add_link(
                    StatementLink(
                        LINK_TYPE_OBJECT,
                        method
                    )
                )

            # Otherwise, we'll default to string constant
            else:

                method = links[i]

                statement.add_link(
                    StatementLink(
                        LINK_TYPE_CONSTANT,
                        method
                    )
                )


    return statement


def replace_delimited_strings_and_save_placeholders(delimiter1, delimiter2, s, placeholders, prefix, inclusive = True, suffix = ""):

    logn( "script debug", "Replace Delimited in:  '%s'" % s )

    # Find first string
    pos = s.find(delimiter1)

    # Loop through all strings
    while ( pos >= 0 ):

        # Find end of string
        end = s.find(delimiter2, pos + 1)

        # Ignore delimited strings.  Should we keep looking?
        while ( (end > pos) and ( (s[end - 1] == "\\") or ( len(s[pos + 1 : end].replace(delimiter1, "")) != len(s[pos + 1 : end].replace(delimiter2, "")) ) ) ):

            # Try again
            end = s.find(delimiter2, end + 1)


        # If we failed to close the string, we abort parsing altogether
        if (end < 0):

            # Abort
            logn( "script error", "Aborting:  Cannot close the string!" )
            sys.exit()

            return None

        else:

            # Current placeholder index
            index = len(placeholders)

            # Calculate a unique name for this placeholder
            placeholder_name = "@^%s:%d$@" % (prefix, index)

            # Create a new placeholder for the string data
            placeholders.append(
                (
                    placeholder_name, 
                    s[pos + int(not inclusive) : (end + 1) - (2 * int(not inclusive))]
                )
            )

            # Update given string to use placeholder.
            # Also add a suffix after the placeholder, if given.
            #print "Before:  '%s'" % s
            s = s[0 : pos + int(not inclusive)] + placeholders[-1][0] + suffix + s[(end + 1) - (1 * int(not inclusive)) : len(s)]
            #print "After:  '%s'" % s
            

            # Find the next string in the expression.
            # We'll start from wherever we previously started, because we just removed the given string and replaced it with a placeholder.
            #  (e.g. command("this").do("that") -> command(@string:0).do("that"), we've already searched through "command(" but haven't yet searched through ").do("that")"...
            pos = s.find(delimiter1, pos + 1 + len(placeholder_name) + (2 * int(not inclusive)) + len(suffix))


    # Return updated string data, plus placeholders.
    return s


def replace_delimited_characters(searches, replace, delimiter1, delimiter2, s):

    # Find first delimiter
    pos = s.find(delimiter1)

    # Loop through all delimited portions of the string
    while ( pos >= 0 ):

        # Find end of string
        end = s.find(delimiter2, pos + 1)

        logn( "script debug", "'%s'" % s[pos : end + 1] )
        logn( "script debug", len( s[pos : end + 1].replace(delimiter1, "") ) != len( s[pos : end + 1].replace(delimiter2, "") ) )

        # Ignore delimited strings.  Should we keep looking?
        while ( (end > pos) and ( (s[end - 1] == "\\") or ( len( s[pos : end + 1].replace(delimiter1, "") ) != len( s[pos : end + 1].replace(delimiter2, "") ) ) ) ):

            # Try again
            end = s.find(delimiter2, end + 1)


        # If we failed to close the string, we abort parsing altogether
        if (end < 0):

            # Abort; return original string.
            return s

        else:

            # Current string length
            len1 = len(s)

            logn( "script debug", ("before", s) )
            # Grab delimited text
            s2 = s[pos + 1 : end]

            logn( "script debug", "Scanning:  '%s'" % s2 )

            # Replace all searched strings
            for search in searches:

                logn( "script debug", "Scanning for:  %s" % search )

                # Update
                s2 = s2.replace(search, replace)

            # Replace characters within delimited range
            s = s[0 : pos + 1] + s2 + s[(end) : len(s)]
            logn( "script debug", ("after", s) )

            # Length after replacement
            len2 = len(s)
            

            # Find the next string in the expression.
            # We'll start from wherever we previously started, because we just removed the given string and replaced it with a placeholder.
            #  (e.g. command("this").do("that") -> command(@string:0).do("that"), we've already searched through "command(" but haven't yet searched through ").do("that")"...
            pos = s.find(delimiter1, end - (len1 - len2))

    return s

