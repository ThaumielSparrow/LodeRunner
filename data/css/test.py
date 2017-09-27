import re


properties_by_selector = {}

def parse_property(p):

    # Check for RGB define
    matches = re.findall( "rgb\(([^)]+?)\)", p )

    # Found one?
    if ( len(matches) > 0 ):

        # Take the first result, we should only have one anyway...
        rgb_string = matches[0]

        return rgb_string


    # Check for quotes, remove if necessary
    matches = re.findall( "\"([^\"]*?)\"", p )

    # Matched?
    if ( len(matches) > 0 ):

        # Return the stuff inside the quotes
        return matches[0]


    # Default to the original property text
    return p


f = open("theme1.css", "r")
data = f.read()
f.close()

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

print css

# grep the string for its selector / descriptor blocks
matches = re.findall( "([^{]*?){([^}]*?)}", css )

# Let's process the results
for (selector, description) in matches:

    # First, get rid of annoying whitespace
    selector = selector.strip()
    description = description.strip()


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
            properties[key] = parse_property(value)


    # Save the current selector's properties...
    properties_by_selector[selector] = properties



for key in properties_by_selector:

    print key
    print ""
    print properties_by_selector[key]
    print ""
