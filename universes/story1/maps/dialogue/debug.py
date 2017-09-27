import os
import subprocess

f = open("debug.txt", "r")
lines = f.readlines()
f.close()

rows = [ s.split(":", 2) for s in lines ]

# Loop results
for (filename, linenumber, match) in rows:

    # Cast line number as integer
    linenumber = int(linenumber)

    # Read file
    f = open(filename, "r")
    lines = f.readlines()
    f.close()

    # Print filename
    print filename

    # Print relevant lines
    print "%s:  %s" % ( linenumber, match.strip() )
    print "%s:  %s" % ( linenumber + 1, lines[-1 + linenumber + 1].strip() )

    # Double-space
    print ""
