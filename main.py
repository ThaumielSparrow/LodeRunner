"""
I'm releasing this under the "The I Really Could Care Less About You Public License."  Read it here:  http://www.revinc.org/pages/license
"""
# Profiling, beta only!
# Remove this for ship!
#import cProfile

import os
import sys

from code.app import App
from code.constants.common import MODE_GAME, MODE_EDITOR, LAYER_FOREGROUND



# Check for --help flag(s)
if (
    any( s in ("-h", "-help", "--help") for s in sys.argv )
):

    # Define lines
    lines = [
        "",
        "    Optional arguments:",
        "",
        "      -f  Run in fullscreen mode for current session",
        "      -B  Disable background music for current session",
        "      -J  Disable gamepad(s) for current session",
        "",
        "    These arguments apply only to the current session.  The",
        "    next time you start the game normally, the game will use",
        "    your previous configuration for fullscreen mode,",
        "    background music, etc.",
        "",
        "    For detailed help, please view the readme.html file.",
        "",
        "    Thank you for playing A Lode Runner Story!",
        ""
    ]

    # Print help data
    print "\n".join(lines)

    # Exit
    sys.exit()



# Are we in game mode, or are we in editor mode?
game_mode = MODE_GAME
#game_mode = MODE_EDITOR

if ( "--edit" in sys.argv ):
    game_mode = MODE_EDITOR

"""
#print "NOTES:\n\n\n"
#print "ADDED HISTORICAL RECORDS.  USE THEM."
#print 5/0
"""
q = None

# Disable joystick spam
if ( (True) or ( "-q" in sys.argv ) ):
    q = open(os.devnull, "w")
    os.dup2(q.fileno(), sys.stdout.fileno())

if (0):
    q = open("debug/debug_all.txt", "w")
    os.dup2(q.fileno(), sys.stdout.fileno())

i = 0
while ( i < len(sys.argv) ):

    # Check for redirect err to file
    # e.g. -err err.txt
    if ( sys.argv[i] == "-err" and i < (len(sys.argv)-1) ):

        # Redirect to given path
        f = open( sys.argv[i + 1], "w" )
        os.dup2( f.fileno(), sys.stderr.fileno() )

    # Loop!
    i += 1



"""
# Force all error output to a file?
if (1):

    f = open("textures.txt", "w")
    os.dup2( f.fileno(), sys.stderr.fileno() )
"""


#q2 = open("debug/debug.txt", "w")
#os.dup2(q2.fileno(), sys.stderr.fileno())

if (False):

    # Load the data...
    f = open(os.path.join("data", "xml", "dialogs.xml"), "r")
    xml = f.read()
    f.close()


    # Set up a root node
    node = XMLParser().create_node_from_xml(xml)

elif (True):
    app = App(game_mode)

    if (0):

        cProfile.run(
            "app.run()"
        )

    elif (0):

        im = app.widget_dispatcher.create_puzzle_intro_menu()

    elif (0):

        pm = app.widget_dispatcher.create_pause_menu().configure({#PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, self.text_renderers["normal"], self.save_controller, self.network_controller, self.universe, self.universe.session, self.widget_dispatcher, self.ref_skilltrees)
            "x": PAUSE_MENU_X,
            "y": PAUSE_MENU_Y,
            "width": PAUSE_MENU_WIDTH,
            "height": PAUSE_MENU_HEIGHT
        })

        pm.create_tab("gamemenu.tabs.game", app.control_center, app.universe)

    else:

        if (game_mode == MODE_GAME):

            lines = [
                "#############################",
                "Todo list.",
                "1.  Update lookup table to contain all fields, innerxml, tooltip, etc.",
                "2.  Add calls for updating branch-specific response enable/disable",
                "3.  I need to examine onload scripts in maps and see if the logic belongs in ",
                "    onvisit.  onload is okay for paths and stuff, but some stuff I might really ",
                "    in onvisit now...",
                "#############################",
                "NEW NOTES:",
                "",
                "It looks as if acquiring an item (via puzzle",
                "room, quest, whatever) doesn't load in",
                "the item's attributes?",
                "",
                "Also, finish implementing the item attribute",
                "result cache code, e.g. on gold pickup...",
                "#############################"
            ]

            #for line in lines:
            #    print line

            #print "\nSkipping program execution.\nDone.\n"
            #print 5/0


            #print "****************\nAttention!\n\nFinish dx < 0 changes, then copy to\ndx > 0.\n\nRemove this intentional crash\nmessage, too!\n****************\n\n"
            #print 5/0

            # If we have the -record flag on, then we'll skip the menu
            if ( "-record" in sys.argv ):

                # Find argument index
                index = sys.argv.index("-record")

                # Validate following argument exists
                if ( (index+1) < len(sys.argv) ):

                    # Get universe/map name
                    (universe_name, map_name) = sys.argv[index+1].split("/")

                    # Create the universe
                    app.create_universe_by_name(universe_name)

                    # Activate the given map
                    app.universe.activate_map_on_layer_by_name(
                        map_name,
                        layer = LAYER_FOREGROUND,
                        game_mode = MODE_GAME,
                        control_center = app.control_center,
                        ignore_adjacent_maps = True
                    )

                    # Remove hesitation for all enemies
                    for e in app.universe.get_active_map().get_entities_by_type(1): # GENUS_ENEMY, blatantly hard-coded
                        e.no_hesitate()

                    # Pause the universe; press INPUT_DEBUG to unpause and begin recording.
                    app.universe.pause()

                    # Run the game (skip menu)
                    app.run()

                # Error
                else:
                    sys.exit("No universe name, map name given for -record argument.  (e.g. -record mainmenu/root.story)")

            # Go to the main menu
            else:

                # Launch menu
                app.menu()

        elif (game_mode == MODE_EDITOR):

            app.run()

    """
    f = open("debug/debug.css.cache.txt", "w")
    o = app.control_center.get_window_controller().get_css_controller()
    f.write( "Found %d cached selectors...\n\n" % len(o.cached_selector_properties) )
    for key in o.cached_selector_properties:
        f.write( "%s\n%s\n\n" % (key, o.cached_selector_properties[key]) )
    f.close()
    """
    #app.generate_images()

else:

    f = open("maps/dummy.txt", "r")
    xml = f.read()
    f.close()

    log( xml )

    node = XMLParser().create_node_from_xml(xml)



    #node.debug()



    x = node.get_nodes_by_tag("planets")[0].get_nodes_by_tag("planet")[0]

    x.debug()


if (q):
    q.close()


# Goodbye message
sys.stderr.write( "Forget you too.\n" )
