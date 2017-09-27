#from xtest import xtest

import os
import shutil

import re

import sys
import traceback

import md5

import datetime
import time
import calendar

from stat import ST_MTIME

import pygame


def log_msg(m):

    return

    # Make sure folder "debug" exists
    if ( not os.path.exists("debug") ):

        # Create folder
        os.mkdir("debug")


    # Log message
    f = open( os.path.join("debug", "debug.messages.txt"), "a" )
    f.write("%s\n" % m)
    f.close()

    log( "logged message:  %s" % m )


# Default logger.  Sometimes we'll disable this.
def log(*args):

    return

    print "%s:" % traceback.format_stack()[-2].split("\n")[0].strip()

    for arg in args:
        print arg,

    print "\n"


# Higher-priority logger.  Sure.
def log2(*args):

    return

    print "%s:" % traceback.format_stack()[-2].split("\n")[0].strip()

    for arg in args:
        print arg,

    print "\n"


# Custom priority logger.
def logn(n, *args):

    valid = False
    if (n in (
        #"latency-correction",
        "network-server",
        "network-client"
    ) ):
        valid = False


    n = "%s" % n
    if ( n.find("error") >= 0 ):

        if ( args[0].find("Abort") >= 0 ):
            for arg in args:
                print arg,
        return

    elif (valid):

        for arg in args:
            sys.stderr.write( "%s " % arg )
        sys.stderr.write("\n")
        return

    else:
        return

    # stderr output?
    if (n == "stderr"):

        # Dump to stderr
        #sys.stderr.write( "%s\n" % ", ".join(args) )
        return

    # Integer level priority?
    elif (
        type(n) == type(1) and
        n >= 3
    ):

        # Print all
        for arg in args:
            print arg,

        # Newline
        print "\n"


        # Check optinoal "detailed" argument
        if ( "--detailed" in args ):

            # Print limited stacktrace
            print "%s:" % traceback.format_stack()[-2].split("\n")[0].strip()

        elif ( "--stacktrace" in args ):

            # Print full stacktrace
            print "\n".join( [s.strip() for s in traceback.format_stack()] )


def debug(string):
    #print string

    return

def insert_char(p_char, p_string, p_position):
    #print p_char, "|", p_string, "|", p_position
    temp_str = ["",""]
    for i in range(0, p_position):
        temp_str[0] = "%s%c" % (temp_str[0], p_string[i])
    for i in range(p_position, len(p_string)):
        temp_str[1] = temp_str[1] + p_string[i]

    return (temp_str[0] + p_char + temp_str[1])

def swap(a, b):
    c = a

    a = b
    b = c

    return (a, b)


def intersect_lengths(r1, r2):

    if ( (r2[0] >= (r1[0] + r1[2])) or ( (r2[0] + r2[2]) <= r1[0] ) or
         (r2[1] >= (r1[1] + r1[3])) or ( (r2[1] + r2[3]) <= r1[1] ) ):

        return (0, 0)

    else:

        (x, y) = (0, 0)

        if ( (r1[0] + r1[2]) > r2[0] ):
            x = (r1[0] + r1[2]) - r2[0]

        else:
            x = (r2[0] + r2[2]) - r1[0]


        if ( (r1[1] + r1[3]) > r2[1] ):
            y = (r1[1] + r1[3]) - r2[1]

        else:
            y = (r2[1] + r2[3]) - r1[1]


        return (x, y)

def intersect(r1, r2, quick=False):

    if (r1 in (None, False) or r2 in (None, False)):
        return False

    if ( (r2[0] >= (r1[0] + r1[2])) or ( (r2[0] + r2[2]) <= r1[0] ) or \
         (r2[1] >= (r1[1] + r1[3])) or ( (r2[1] + r2[3]) <= r1[1] ) ):
        return False

    #return xtest(r1[0], r1[1], r1[2], r1[3], r2[0], r2[1], r2[2], r2[3])

    if (quick == True):
        return True

    else:
        # Now, calculate the intersection rect
        new_rect = (0, 0, 0, 0)
        x = 0
        y = 0
        w = 0
        h = 0

        if (r1[0] < r2[0]):
            x = r2[0]
        else:
            x = r1[0]

        if (r1[1] < r2[1]):
            y = r2[1]
        else:
            y = r1[1]

        if ( (r1[0] + r1[2]) > (r2[0] + r2[2]) ):
            w = (r2[0] + r2[2]) - x
        else:
            w = (r1[0] + r1[2]) - x

        if ( (r1[1] + r1[3]) > (r2[1] + r2[3]) ):
            h = (r2[1] + r2[3]) - y
        else:
            h = (r1[1] + r1[3]) - y

        new_rect = (x, y, w, h)

        return new_rect
        #return True

def intersect_y(r1, r2):

    if ( (r1[1] + r1[3]) <= r2[1] or r1[1] >= (r2[1] + r2[3]) ):
        return False

    else:
        return True

# Is r1 entirely within r2?
def rect_within_rect(r1, r2):

    if ( (r1[0] >= r2[0]) and ( (r1[0] + r1[2]) <= (r2[0] + r2[2]) ) and
         (r1[1] >= r2[1]) and ( (r1[1] + r1[3]) <= (r2[1] + r2[3]) ) ):

        return True

    else:

        return False

def intersect_any(r_single, r_array):
    for r in r_array:
        if (intersect(r_single, r)):
            return True

    return False

def offset_rectOLD(p_rect, x, y):
    return (p_rect[0] + x, p_rect[1] + y, p_rect[2], p_rect[3])

def offset_rect(r, x = 0, y = 0, w = 0, h = 0):
    return (r[0] + x, r[1] + y, r[2] + w, r[3] + h)

def get_bounding_rect(rect_list):
    x1 = rect_list[0][0]
    y1 = rect_list[0][1]

    x2 = x1 + rect_list[0][2]
    y2 = y1 + rect_list[0][3]

    for i in range(1, len(rect_list)):
        if (rect_list[i][0] < x1):
            x1 = rect_list[i][0]

        if (rect_list[i][1] < y1):
            y1 = rect_list[i][1]

        if (rect_list[i][0] + rect_list[i][2] > x2):
            x2 = rect_list[i][0] + rect_list[i][2]

        if (rect_list[i][1] + rect_list[i][3] > y2):
            y2 = rect_list[i][1] + rect_list[i][3]

    bounding_rect = (x1, y1, x2 - x1, y2 - y1)

    return bounding_rect

def rect_contains_point(r, tuple_point):

    (x, y) = tuple_point

    if (x < r[0] or x > (r[0] + r[2]) or y < r[1] or y > (r[1] + r[3])):
        return False

    return True

def line_intersects_rect(l, r):

    x1 = r[0]
    x2 = r[0] + r[2]

    y1 = r[1]
    y2 = r[1] + r[3]


    m = None

    ix1 = (x1 - l[0])
    ix2 = (x2 - l[0])

    iy1 = l[1]
    iy2 = l[1] + l[3]

    if (l[0] == l[2]):
        m = compute_slope(l)

        iy1 = l[1] + (ix1 * m)
        iy2 = l[1] + (ix2 * m)

    #print r, " contains ", l, "???"
    #print (x1, y1)
    #print (x2, y2)
    #print "\n"

    # test x-axis
    if ( (l[0] <= x2) and ((l[0] + l[2]) >= x1) ):

        a = min(l[1], (l[1] + l[3]))
        b = max(l[1], (l[1] + l[3]))

        # test y-axis
        if ( (a <= y2) and (b >= y1) ):

            if ( (iy1 >= r[1] and iy1 <= (r[1] + r[3])) ):
                return True


            if ( (iy2 >= r[1] and iy2 <= (r[1] + r[3])) ):
                return True

    return False

def between(p1, p2, increment):
    r = []

    i = p1
    while (i < p2):
        r.append(i)
        i += increment

    r.append(p2)

    return r

def compute_slope(line):
    return (float( (line[1] + line[3]) - line[1] ) / float( (line[0] + line[2]) - line[0] ))

# Ok, here's the deal.  high_mod works
# just like typical mod, but if the
# result of mod = 0, then high_mod
# changes the result to the divisor.

def high_mod(val, mod):
    i = val % mod
    if (i == 0):
        i = mod

    return i

def strip_alpha(s):
    valid_characters = "0123456789"

    result = ""

    for i in range(0, len(s)):
        if (s[i] in valid_characters):
            result += s[i]

    return result

def strip_numbers(s):
    invalid_characters = "0123456789"

    result = ""

    for i in range(0, len(s)):
        if ( not (s[i] in invalid_characters) ):
            result += s[i]

    return result

def true_sort(some_list):

    results = []
    exceptions = [] # anything that doesn't have a number in it...

    valid_characters = "0123456789"

    for each in some_list:

        # First, we only care about what comes before the - (e.g. Level 51 - Rotation 2 ... we don't care about the 2)
        filename = each.split("-")[0]
        #each = each.split("-")[0]

        # strip out all non-numerical characters
        numerical_value = ""

        for i in range(0, len(filename)):

            if (filename[i] in valid_characters):
                numerical_value += each[i]

        if (numerical_value == ""):
            exceptions.append( [-1, each] )

        else:
            results.append( [int(numerical_value), each] )

    #print 5/0

    # Sort our valid results
    results.sort()

    # Append any exceptions
    results.extend(exceptions)

    # Now build a final results list
    final_results = []

    for (index, value) in results:
        final_results.append(value)

    return final_results

def escape_commas(data):

    inside_quote = False

    final_string = ""

    i = 0

    while (i < len(data)):

        if (data[i] == "\""):
            inside_quote = (not inside_quote)
            final_string += data[i]

        elif (data[i] == ","):
            if (inside_quote):
                final_string += "&#44;"
            else:
                final_string += ","

        else:
            final_string += data[i]

        i += 1

    return final_string

def unescape_commas(data):
    return data.replace("&#44;", ",")

def get_percent(a, b):

    if (b == 0):
        return 0

    return float(a) / float(b)


# Guarantee that a given path exists.
# Returns the path (which now definitely exists).
def ensure_path_exists(path):

    pieces = path.split( os.path.sep )

    for i in range(0, len(pieces)):

        path = os.path.sep.join(pieces[0 : i + 1])

        if (not os.path.exists(path)):

            os.mkdir(path)

    # Return path
    return path


def ensure_path_exists2(path_tuple):

    for i in range(0, len(path_tuple)):

        path = os.path.sep.join(path_tuple[0 : i+1])

        if (not os.path.exists(path)):
            os.mkdir(path)

def format_timedelta(a, b):

    delta = abs(a - b)

    (months, remainder) = divmod(delta, (60 * 60 * 24 * 30))

    (days, remainder) = divmod(remainder, (60 * 60 * 24))

    (hours, remainder) = divmod(remainder, (60 * 60))

    (minutes, seconds) = divmod(remainder, 60)

    if (months > 0):

        return "%d month%s, %d day%s" % (months, ("s" * int( months != 1 )), hours, ("s" * int( hours != 1 )))

    elif (days > 0):

        return "%d day%s, %d hour%s" % (days, ("s" * int( days != 1 )), hours, ("s" * int( hours != 1 )))

    elif (hours > 0):

        return "%d hour%s, %d minute%s" % (hours, ("s" * int( hours != 1 )), minutes, ("s" * int( minutes != 1 )))

    elif (minutes > 0):

        return "%d minute%s, %d second%s" % (minutes, ("s" * int( minutes != 1 )), seconds, ("s" * int( seconds != 1 )))

    else:

        return "%d second%s" % (seconds, ("s" * int( seconds != 1 )))

def format_framecount_as_time(frames, format = "stopwatch"):

    # Right now I'm just going to do stopwatch formatting.  Maybe some day I'll want other modes...
    if (True): # if (format == "stopwatch")

        # Count total seconds
        seconds = int(frames / 60) # 60FPS (hard-coded)

        # Just count minutes and seconds
        (minutes, seconds) = divmod(seconds, 60)


        # Convert each to a string
        minutes = "%d" % minutes
        seconds = "%d" % seconds


        # Always use a leading 0 for seconds, if/a
        if ( len(seconds) == 1 ):
            seconds = "0%s" % seconds


        # Return formatted time
        return "%s:%s" % (minutes, seconds)

# Get the current system time as a formatted string.
# I probably only will use this for "Last Played" strings, and I will probably only use the one format.
def get_formatted_time(timestamp, format = "normal"):

    # Just this one format for now
    if (format == "normal"):

        # Get various time data for the current moment in time
        today = datetime.datetime.fromtimestamp(timestamp)#today()

        # Grab the info we care about
        (month, day, hour, minute) = (
            today.month,
            today.day,
            today.hour,
            today.minute
        )

        # I want minute to have leading zeroes, so I'm going to cast
        # as a string and then do a length check.
        minute = "%d" % minute

        # Leading zero needed?
        if ( len(minute) == 1 ):
            minute = "0%s" % minute
        

        # Format string
        return "%s %s   %s:%s" % (
            calendar.month_name[month][0:3], # It's okay if we go out of bounds, it'll then just use the entire month name (maybe some non-English month name?)
            day,
            hour,
            minute
        )

    # Maybe some day I'll want different formats...
    else:

        return "Unknown Date"


def f2():

    for each in os.listdir("."):

        (a, b) = (
            get_file_modified_time(each),
            int( time.time() )
        )

        log( "%s:  %s" % (each, format_timedelta(a, b)) )

def wrap_degrees(degrees):

    while (degrees < 0):
        degrees += 360

    while (degrees >= 360):
        degrees -= 360

    return degrees

def wrap_index_at_position(position, index):

    l = PLANETARY_RING_LENGTHS[position]

    while (index < 0):
        index += l

    while (index >= l):
        index -= l

    return index

def wrap_rect_for_circumference(r, circumference):

    log( "wrap_rect:  ", r )

    rects = [r]

    if (r[0] < 0):

        sub1 = ( (circumference + r[0]), r[1], -r[0], r[3])

        sub2 = (0, r[1], (r[2] + r[0]), r[3])

        rects = [sub1, sub2]

    elif (r[0] + r[2] > circumference):

        sub1 = (r[0], r[1], (circumference - r[0]), r[3])

        sub2 = (0, r[1], ( (r[0] + r[2]) - circumference), r[3])

        rects = [sub1, sub2]

    return rects

def arc_between(a, b):

    a = wrap_degrees(a)
    b = wrap_degrees(b)

    arc = 0

    if (a > b):
        arc = a - b

    else:
        arc = b - a


    if (arc > 180):
        arc = (360 - arc)

    return arc

def angle_falls_within_arc(angle, a, b):

    if (a == None or b == None):
        return True

    elif (a == b):
        return True

    else:


        if (b < a):
            return (not angle_falls_within_arc(angle, b, a))

        else:

            #if (b < a):
            #    b += 360


            if (angle >= a and angle <= b):
                return True

            else:
                return False


def angle_greater_than(a, b):

    #if (arc_between(a, b)
    return

def arc_intersection(arc1, arc2):

    if (arc1[0] == arc1[1]):

        return arc2

    elif (arc2[0] == arc2[1]):

        return arc1

    elif ( (not angle_falls_within_arc(arc1[0], arc2[0], arc2[1])) and
         (not angle_falls_within_arc(arc1[1], arc2[0], arc2[1])) ):

        return (None, None) # ?

    elif (arc1[0] <= arc2[0]):

        return (arc2[0], arc1[1])

    elif (arc2[0] <= arc1[0]):

        return (arc1[0], arc2[1])

def arc_contains_arc(arc1, arc2):

    # An infinite arc contains every arc
    if (arc1[0] == arc1[1]):
        return True


    #print "param1:  ", arc1
    #print "param2:  ", arc2, "\n"


    if (arc1[1] < arc1[0]):
        arc1 = (arc1[0], arc1[1] + 360)

        if (arc2[1] < arc2[0]):
            arc2 = (arc2[0], arc2[1] + 360)

        #else:
        #    arc2 = (360 + arc2[0], 360 + arc2[1])

    elif (arc2[1] < arc2[0]):
        arc2 = (arc2[0], arc2[1] + 360)


    log( "wrapped1:  ", arc1 )
    log( "wrapped2:  ", arc2, "\n\n" )


    if (arc2[0] < arc1[0] or arc2[1] > arc1[1]):
        return False

    else:
        return True

def shorter_arc(a, b):

    #print "checking shorter arc:  ", a, " -vs- ", b

    if (a == b):
        return (a, b)


    (u, v) = (a, b)


    if (abs(u - v) == 180):
        #print (a, b)
        return (a, b)

    elif (abs(u - v) > 180):

        if (a > 0 and b < 0):
            #print (b, a)
            return (b, a)

        elif (b > 0 and a < 0):
            return (a, b)

        else:
            #print (a, b)
            return ( max(a, b), min(a, b) )

    else:

        if (a < b):
            #print (a, b)
            return (a, b)

        else:
            #print (b, a)
            return (b, a)

def xml_encode(s):
    return s.replace("'", "&apos;").replace("<", "&lt;").replace(">", "&gt;")

def xml_decode(s):
    return s.replace("&apos;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")

def f2i(x):

    if (x >= 0):

        return int(x + 0.001)

    else:

        return int(x - 0.001)

def cf(f):

    if (f >= 0):

        return (f + 0.001)

    else:

        return (f - 0.001)


def resize_image(path_old, path_new, ratio = None, size = None):

    if (not os.path.exists(path_old)):

        log( "resize_image error:  path '%s' does not exist..." % path_old )

    else:

        # Load old image
        surface = pygame.image.load(path_old)

        (ow, oh) = (
            surface.get_width(),
            surface.get_height()
        )

        # Create a new surface, scaled...
        (w, h) = (0, 0)


        if (size == None):

            (w, h) = (
                int(ratio * surface.get_width()),
                int(ratio * surface.get_height())
            )

        else:

            (w, h) = size


        # I'm going to create the thumbnail based on the middle 50% of the source surface to preserve some legibility...
        midsurface = pygame.surface.Surface((w*2, h*2)).convert()

        midsurface.blit(surface, (0, 0), (int(ow / 4), int(oh / 4), 2 * int(ow / 4), 2 * int(oh / 4)))


        surface2 = pygame.surface.Surface((w, h)).convert()

        # Blit the old data onto the new surface...
        #surface2.blit(surface, (0, 0, w, h), (0, 0, surface.get_width(), surface.get_height()))
        surface2 = pygame.transform.scale(midsurface, (w, h))

        # Save the new surface (the scaled surface) to image...
        pygame.image.save(surface2, path_new)

def sort_files_by_date(files, ascending = False):

    temp_list = [] # [modified, filename]

    for each in files:

        stat = os.stat(each)
        mod_time = stat[ST_MTIME]

        temp_list.append( [mod_time, each] )

    temp_list.sort()

    if (not ascending):
        temp_list.reverse()

    files = []

    for result in temp_list:

        files.append(result[1])

    return files

def get_file_modified_time(path):

    if (os.path.exists(path)):

        stat = os.stat(path)

        return stat[ST_MTIME]

    else:

        return 0

# This function takes some value (typically a parameter from an XML menu)
# and calculates the appropriate integer value it represents.  For percentage-based
# calculations, it will use the "ceiling" value to determine the proper result.
# For raw values, it will simply return the raw value (with no regard for the "ceiling").
def evaluate_spatial_expression(value, ceiling):

    # Force potential integers into string form (hacky)
    value = "%s" % value

    if (value.endswith("%")):

        # Strip % symbol
        phrase = value.rstrip("%")

        # Calculate percentage
        percentage = float( float(phrase) / 100.0)

        # Calculate available cell width
        spatial_width = ceiling

        # Calculate final width
        return int(percentage * spatial_width)

    else:

        return int(value)


# Old, homemade version... bad to use?
def clear_folder(path):

    files = os.listdir(path)

    for f in files:

        if ( os.path.isdir( os.path.join(path, f) ) ):

            clear_folder( os.path.join(path, f) )
            #os.rmdir( os.path.join(path, f) )

        else:

            os.remove( os.path.join(path, f) )

    os.rmdir(path)


def remove_folder(path):

    if (os.path.exists(path)):

        shutil.rmtree(path)


def copy_folder(path_from, path_to):

    if (os.path.exists(path_from)):

        shutil.copytree(path_from, path_to)


def create_path(path, base = None):

    # Split into individual folders
    folders = path.split( os.path.sep )


    # Where to place the new folder?
    target_path = folders[0]

    if (base != None):

        target_path = os.path.join(base, folders[0])


    # Make sure base folder exists
    if (not os.path.exists(target_path)):

        os.mkdir(target_path)


    # If remaining folders exist within this folder, process them using the target_path as the base...
    if (len(folders) > 1):

        create_path(
            os.path.sep.join(folders[1 : len(folders)]),
            base = target_path
        )


def set_alpha_for_glcolor(alpha, glcolor):

    if (glcolor):

        return (glcolor[0], glcolor[1], glcolor[2], alpha)

    else:

        return None


def set_alpha_for_rgb(alpha, rgb):

    if (rgb):

        return (rgb[0], rgb[1], rgb[2], alpha)

    else:

        return None


def rgb_to_glcolor(rgb):

    if (not rgb):
        return (0, 0, 0, 0)

    r = rgb[0] / 255.0
    g = rgb[1] / 255.0
    b = rgb[2] / 255.0

    if (len(rgb) > 3):
        return (r, g, b, rgb[3])

    else:
        return (r, g, b, 1.0)


def rgb_to_hex(rgb):

    if (not rgb):
        return "#000000"

    return "#%s%s%s" % (
        hex(rgb[0])[2:4],
        hex(rgb[1])[2:4],
        hex(rgb[2])[2:4]
    )


def parse_rgb_from_string(s):

    rgb = s.split(",")

    if ( len(rgb) == 3 ):

        return (
            int( rgb[0].strip() ),
            int( rgb[1].strip() ),
            int( rgb[2].strip() )
        )

    elif ( len(rgb) == 4 ):

        return (
            int( rgb[0].strip() ),
            int( rgb[1].strip() ),
            int( rgb[2].strip() ),
            float( rgb[3].strip() )
        )

    else:
        return None


def translate_rgb_to_string(rgb):

    if ( len(rgb) == 3 ):

        return "%d,%d,%d" % (rgb[0], rgb[1], rgb[2])

    else:

        return ""


def increment_glcolor_by_n_gradient_steps(glcolor, n, tstepRGB):

    return (
        glcolor[0] + n * tstepRGB[0],
        glcolor[1] + n * tstepRGB[1],
        glcolor[2] + n * tstepRGB[2],
        glcolor[3] + n * tstepRGB[3]
    )


def multiply_glcolor_by_coefficient(glcolor, coefficient):

    return (
        glcolor[0] * coefficient,
        glcolor[1] * coefficient,
        glcolor[2] * coefficient,
        glcolor[3]
    )

def multiply_glcolor_alpha_by_coefficient(glcolor, coefficient):

    return (
        glcolor[0],
        glcolor[1],
        glcolor[2],
        glcolor[3] * coefficient
    )


# Get the first non-null (not "None," anyway...) value
def coalesce(*values):

    # Try to find a non-None value
    for i in range( 0, len(values) ):

        # Found a non-None item?
        if ( values[i] != None ):

            # Return it!
            return values[i]


    # Well, we'll still have "None" if we have no value given (or every value is None).
    return None


# Evaluate whether or not a given string is numeric
def is_numeric(s):

    # We can strip whitespace, if nothing else.  "0  " will still evaulate to 0.
    s = s.strip()


    # If the string starts with a negative sign, then that's ok.  We'll strip it here...
    if ( s.startswith("-") ):

        # Just drop the leading negative sign.
        s = s[ 1 : len(s) ]


    # If we have an empty string, then we don't have a numeric string...
    if ( len(s) == 0 ):

        return False

    else:

        # Strip out everything except for numbers and decimals
        subbed = re.sub( "[^\.0-9]", "", s)

        # If the string changed at all, we don't have a numeric string
        if ( len(subbed) < len(s) ):

            return False

        # Also, if we have more than one period in the remaining string, then it's a bad number (e.g. no such number as 23423.0.5)
        else:

            # Strip out numbers, leaving only a single decimal, presumably
            subbed2 = re.sub( "[0-9]", "", subbed )

            # If more than one character remains (i.e. > 1 decimal), then this isn't quite a numeric string...
            if ( len(subbed2) > 1 ):

                return False

            # Otherwise, this is a valid number
            else:

                return True

# Separate a semicolon-separated string into values
def ssv_unpack(ssv):

    # Results
    results = []

    # Parse
    pieces = ssv.split(";")

    # Loop
    for piece in pieces:

        # Sanity
        if ( len( piece.strip() ) > 0 ):

            # Track
            results.append( piece.strip() )

    # Return results
    return results


# "Safely" round a float
def safe_round(x, digits):

    # Cast float to string
    s = "%s" % x

    # If no decimal exists, return immediately
    if ( s.find(".") == -1 ):

        # True integer
        return s

    # Otherwise, avoid long float (e.g. 24.000000001)
    else:

        # Split into integer and decimal portion
        (a, b) = s.split(".")

        # Trim decimal portion if necessary
        if ( len(b) > digits ):

            # Trim
            b = b[ 0 : digits ]

        # Return desired accuracy
        return "%s.%s" % (a, b)


# Generate a unique ID for a string based on its text
def generate_string_id(s):

    # Create new md5 object
    m = md5.new()

    # Enter string
    m.update(s)

    # Return 32 character hex string
    return m.hexdigest()


# Get a flag value (data located in user/flags.xml).
# Requires an xml parser because I can't include code.tools.xml
# from within this file (infinite import loop) and I'm too
# lazy to fix it properly for 2 calls to this function.
def get_flag_value(name, parser):

    # Check for special flags file
    if ( os.path.exists( os.path.join("user", "flags.xml") ) ):

        # Read in xml
        node = parser.create_node_from_file( os.path.join("user", "flags.xml") )

        # Validate node
        if (node):

            # Find flags root
            ref_flags = node.find_node_by_tag("flags")

            # Validate again
            if (ref_flags):

                # Loop each flag ref
                for ref_flag in ref_flags.get_nodes_by_tag("flag"):

                    # Sound debug flag?
                    if ( ref_flag.get_attribute("name") == name ):

                        # Look for value
                        ref_value = ref_flag.find_node_by_tag("value")

                        # Validate
                        if (ref_value):

                            # Return the value
                            return ref_value.innerText.strip()

    # Nothing found
    return None
