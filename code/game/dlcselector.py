import os
import sys

import copy

import pygame

from code.extensions.common import UITemplateLoaderExt

from code.render.glfunctions import *

from code.controllers.intervalcontroller import IntervalController
from code.controllers.menucontroller import MenuController
from code.controllers.timercontroller import TimerController

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser

from code.utils.common import is_numeric, xml_encode, xml_decode, log, log2, logn

from code.game.map import Map

from code.constants.common import MODE_GAME, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT
from code.constants.paths import UNIVERSES_PATH

from code.constants.newsfeeder import NEWS_GENERIC_ITEM

from code.constants.sound import *


# Radius of the spotlight we'll use for each universe's preview maps
PREVIEW_RADIUS = 100

# Padding on either side (left/right) of the preview thing
PREVIEW_PADDING = 20

# Height of any given selection (we'll render a bit of a background / highlight behind the active selection).
OPTION_HEIGHT = int(0.5 * SCREEN_HEIGHT)

# The top and the bottom of the selection screen will "taper" into blackness (gradient)
TAPER_AREA_SIZE = 80


# A wrapper to house data related to the options a player will choose from when selecting from available dlc downloads.
class DLCSelectorOption:

    def __init__(self, name, version, title, label, bytes, files):

        # Track the name of the option (i.e. the universe's name, which folder name we'll return to have loaded)
        self.name = name

        # Track the version of this download, in case we re-release an existing DLC with updates (e.g. fixes)
        self.version = version

        # The title of the dlc option (i.e. level set title)
        self.title = title

        # Optional label for the dlc option (e.g. New, Update Available)
        self.label = label


        # Size of the dlc download in bytes (for all files:  maps, etc.)
        self.bytes = bytes


        # A list of hashes defining which files we will download to which locations for this level set
        self.files = files


        # Any visible header (usually just the title of the dlc level pack)
        self.headers = []

        # Visible subheaders (e.g. download size); we'll render these in a dimmer font
        self.subheaders = []

        # Paragraph data (description of the download), each rendered as its own paragraph.
        self.paragraphs = []


        # We'll hope to create a simple image to display next to each DLC option, a still-frame we try to download from the webserver
        self.preview = None


    # Basic configuration
    def configure(self, options):

        if ( "name" in options ):
            self.name = options["name"]

        if ( "title" in options ):
            self.title = options["title"]


        # For chaining
        return self


    # Add a header
    def add_header(self, header):

        # As many as we want, I guess
        self.headers.append(header)


    # Add a subheader
    def add_subheader(self, subheader):

        # We really probably only will ever use one of these, but who knows?
        self.subheaders.append(subheader)


    # Add a new paragraph (i.e. sell job!)
    def add_paragraph(self, paragraph):

        # We might use more than one of these... though screen space is fairly limited...
        self.paragraphs.append(paragraph)


    # Try to load a preview image from a given filepath.  We should have downloaded some preview image for each dlc option from the webserver.
    def load_preview_from_path(self, path, control_center):

        log2( "path = %s" % path )

        # Validate that the path exists
        if ( os.path.exists(path) ):

            # Create a graphic widget for the preview
            self.preview = control_center.get_widget_dispatcher().create_graphic().configure({
                "filename": path,
                "file-width": int(2 * PREVIEW_RADIUS),
                "file-height": int(2 * PREVIEW_RADIUS)
            })

            # Force a load image call
            self.preview.load_image()

            # Force the alpha controller to full visibility
            self.preview.alpha_controller.configure({
                "interval": 1.0
            })


    # Get dlc option name
    def get_name(self):

        return self.name


    # Get dlc level set title
    def get_title(self):

        return self.title


    # Get dlc level set label
    def get_label(self):

        return self.label


    # Set dlc level set label
    def set_label(self, label):

        # Set
        self.label = label


    # Get the size (in bytes) of this level set option
    def get_size_in_bytes(self):

        return self.bytes


    # Get the file hashes
    def get_files(self):

        # Return files
        return self.files


    # Render the preview image, if we managed to load it...
    def draw_preview(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller, active = True):

        # Did we load it?
        if (self.preview):

            # Render the preview image
            self.preview.draw(sx - PREVIEW_RADIUS, sy - PREVIEW_RADIUS, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


        # Now render a spotlight effect on top of the active preview(s)
        window_controller.get_geometry_controller().draw_exclusive_circle_with_radial_gradient(sx, sy, PREVIEW_RADIUS, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


    # Render any label data above/below the preview
    def draw_labels(self, sx, sy, text_renderer, window_controller, active = True):

        # Deprecated

        """
        # Define string to render
        text = self.get_title()

        # Render this universe's title above the preview
        if (active):

            # Bright font
            text_renderer.render_with_wrap(text, sx - PREVIEW_RADIUS, sy - PREVIEW_RADIUS - int(0.0 * text_renderer.font_height), (225, 225, 225), align = "left", color_classes = color_classes)

        else:

            # Dim font
            text_renderer.render_with_wrap(text, sx - PREVIEW_RADIUS, sy - PREVIEW_RADIUS - int(0.0 * text_renderer.font_height), (125, 125, 125), align = "left", color_classes = color_classes)
        """


    # Render completion data for the given option in a single player universe.  Width and height represents the area we should render within.
    # Return the number of lines we rendered. (?)
    def draw_description_data(self, sx, sy, width, height, text_renderer, active = True):

        # Track rendering position
        (rx, ry) = (
            sx,
            sy
        )


        # Default colors
        (text_normal, text_dim, text_gold) = (
            (225, 225, 225),
            (175, 175, 175),
            (192, 160, 40)
        )

        # Dim everything if this option is not the active selection
        if (not active):

            # Overwrite
            (text_normal, text_dim, text_gold) = (
                (175, 175, 175),
                (125, 125, 125),
                (152, 125, 30)
            )


        # Does a label exist?
        if ( self.get_label() != "" ):

            # Format text
            text = "[color=special]%s[/color]" % self.get_label()

            # Define potential color classes
            color_classes = {
                "special": (237, 128, 35)
            }

            # Render label in upper-right corner
            text_renderer.render_with_wrap(text, rx + width - 20, ry, text_normal, max_width = width, align = "right", color_classes = color_classes)


        # Begin by rendering each header
        for i in range( 0, len(self.headers) ):

            # Render each one as its own line
            ry += text_renderer.render_with_wrap(self.headers[i], rx, ry, text_normal, max_width = width)

        # Next, render any subheader using a dimmed color
        for i in range( 0, len(self.subheaders) ):

            # Each one gets its own line
            ry += text_renderer.render_with_wrap(self.subheaders[i], rx, ry, text_dim, max_width = width)


        # Now render each paragraph, double-spacing before we render each one...
        for i in range( 0, len(self.paragraphs) ):

            # Double-space
            ry += text_renderer.font_height

            # Render paragraph
            ry += text_renderer.render_with_wrap(self.paragraphs[i], rx, ry, text_dim, max_width = width)


        # (?) Return the amount of screen space we used while rendering the completion summary
        return (ry - sy)


# An object that allows the player to view all of the available dlc level sets.
# If they select one, we'll add a menu that confirms the download, then proceed with the downloading.
class DLCSelector(UITemplateLoaderExt):

    def __init__(self):

        UITemplateLoaderExt.__init__(self)


        # The dlc selector will have its own isolated menu controller object
        self.menu_controller = MenuController()

        # It'll also have a local timer controller
        self.timer_controller = TimerController()


        # Control cursor lock globally within this dlc selector
        self.cursor_locked = False

        # After downloading a level, we'll activate a flag so the selection loop can remove label
        self.active_download_complete = False


        # If the player selects a level set to download, we'll "remember" the title in this variable.
        self.current_option_title = ""

        # Similarly, we'll "remember" the size (in bytes) of the current option
        self.current_option_size_in_bytes = 10000 # We'll overwrite this...


    # Check to see which version, if any, the user has of a given universe by name
    def check_universe_version(self, name):

        # Generate path for universe's meta file
        path = os.path.join(UNIVERSES_PATH, name, "meta.xml")


        # Validate
        if ( os.path.exists(path) ):

            # Read in the xml data, then search for the version tag
            ref_version = XMLParser().create_node_from_file(path).find_node_by_tag("version")

            # Validate
            if (ref_version):

                # Return version string
                return ref_version.innerText


        # Version not found
        return None


    # Given a node that defines each available download, create a set of options (i.e. each dlc level set)
    # for the user to browse.
    def select_using_node(self, ref_downloads, tilesheet_sprite, additional_sprites, control_center):

        # Prepare a list of options (all of the universes)
        options = []


        # Track the current cursor selection
        current_option = 0

        # When we move from one option to another, we'll instantly move the cursor (for selection logic),
        # but the player will see a gradual scroll.
        current_scroll = 0


        # Each universe will have a set of "preview" maps that give the user a visual indicator / reminder of the universe
        # they are looking at.  Also, each universe will (likely) provide some bit of completion data to the user.
        for ref_download in ref_downloads.get_nodes_by_tag("download"):

            # Peek to find the name / title / size in bytes for this dlc option
            (name, version, title, bytes) = (
                ref_download.find_node_by_tag("name").innerText,
                ref_download.find_node_by_tag("version").innerText,
                ref_download.find_node_by_tag("title").innerText,
                int( ref_download.find_node_by_tag("bytes").innerText ) # Cast as int
            )

            # Prepare a list of file hashes
            files = []

            # Loop given files
            for ref_file in ref_download.find_node_by_tag("files").get_nodes_by_tag("file"):

                # Define file info
                files.append({
                    "path": ref_file.find_node_by_tag("folder").innerText, # Where to save the download
                    "url": ref_file.find_node_by_tag("url").innerText, # Where to download from (on the server)
                    "bytes": int( ref_file.find_node_by_tag("bytes-compressed").innerText ), # Size of this file download
                    "type": ref_file.find_node_by_tag("type").innerText, # typically "archive" or "n/a"
                    "binary": ( int( ref_file.find_node_by_tag("binary").innerText ) == 1 ) # Write binary data?
                })


            # Assume no special label for this option
            label = ""

            # Get existing version for this DLC
            existing_version = self.check_universe_version(name)
            logn( "dlc version", "Existing version for '%s':  %s\n" % (name, existing_version) )

            # No version exists?  (Not yet downloaded)
            if (existing_version == None):

                # "New!"
                label = "New!"

            # Updated version exists?
            elif (existing_version < version):

                # "Updated!"
                label = "Update Available!"


            # Create an option we'll use to track data for this level set
            option = DLCSelectorOption(name, version, title, label, bytes, files)


            # Read in headers
            ref_headers = ref_download.find_node_by_tag("headers")

            # Validate
            if (ref_headers):

                # Grab each header
                for ref_header in ref_headers.get_nodes_by_tag("header"):

                    # Add it to the option
                    option.add_header( ref_header.innerText )


            # Read in subheaders
            ref_subheaders = ref_download.find_node_by_tag("subheaders")

            # Validate
            if (ref_subheaders):

                # Grab each subheader
                for ref_subheader in ref_subheaders.get_nodes_by_tag("subheader"):

                    # Add the subheader
                    option.add_subheader( ref_subheader.innerText )


            # Read in paragraphs
            ref_paragraphs = ref_download.find_node_by_tag("paragraphs")

            # Validate
            if (ref_paragraphs):

                # Grab each paragraph
                for ref_paragraph in ref_paragraphs.get_nodes_by_tag("paragraph"):

                    # Add the paragraph
                    option.add_paragraph( ref_paragraph.innerText )


            # Check for a preview
            ref_preview = ref_download.find_node_by_tag("preview")

            # Validate
            if (ref_preview):

                # Load from path.  Does nothing if the path does not exist.
                option.load_preview_from_path( os.path.join("tmp", ref_preview.innerText), control_center )
            

            # Add the new option to our list of universe options
            options.append(option)


        # As we move into the block that renders all of the options, we're going to want a couple of shortcuts to some of the controllers.
        window_controller = control_center.get_window_controller()

        # Handle to the input controller
        input_controller = control_center.get_input_controller()

        # Obviously we'll have text to draw
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()

        # Let's grab the scissor controller as well
        scissor_controller = control_center.get_window_controller().get_scissor_controller()


        # Now let's do one last thing:  I want to load in a Ui widget to serve as the "backdrop" for this
        # selector page.  It's just a header, like on the main menu, except we'll scroll it away as we move
        # from one universe option to another.
        # Fetch the widget dispatcher
        template = self.fetch_xml_template("dlcselector.backdrop").add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % int(PAUSE_MENU_Y / 2) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create the local backdrop widget
        backdrop_widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, None)

        backdrop_widget.set_id("universeselector-backdrop")
        #self.backdrop_widget.focus()


        # FPS timer
        clock = pygame.time.Clock()

        # Select loop
        while True:

            # Target 60fps (hard-coded)
            clock.tick(60)

            # Clear backbuffer
            #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            clear_buffers()

            # Clear to black
            window_controller.get_geometry_controller().draw_rect(0, 0, window_controller.render_width, window_controller.render_height, (0, 0, 0))


            # Poll keyboard input
            (events, keypresses) = (
                pygame.event.get(),
                pygame.key.get_pressed()
            )

            # Feed input controller
            input_controller.poll_and_update_system_input(events, keypresses)
            input_controller.poll_and_update_gameplay_input( input_controller.get_system_input(), keypresses )

            # Read back abstracted input data
            system_input = input_controller.get_system_input()
            gameplay_input = input_controller.get_gameplay_input()


            # Check the active download complete flag
            if (self.active_download_complete):

                # Disable flag
                self.active_download_complete = False

                # Remove label on current selection
                options[current_option].set_label("")



            # ** Debug - Abort
            if ( (K_F11 in input_controller.get_system_input()["keydown-keycodes"]) ):
                return "asdf?"
            if ( (K_F12 in input_controller.get_system_input()["keydown-keycodes"]) ):
                log( 5/0 )


            # If we haven't yet made a selection, we will check for cursor control
            if (not self.cursor_locked):

                # Perhaps the user wants to cancel, go back to the menu?
                if (
                    (K_ESCAPE in input_controller.get_system_input()["keydown-keycodes"]) or
                    ( input_controller.check_gameplay_action("escape", system_input, [], True) )
                ):

                    # Lock cursor, no point in checking input now...
                    self.cursor_locked = True

                    # App fade, followed by a "cancel" event on this selector
                    window_controller.fade_out(
                        on_complete = "dlcselector:cancel"
                    )

                # Cursor up?
                if (INPUT_SELECTION_UP in gameplay_input):

                    # Move up one
                    current_option -= 1

                    # Wrap around?
                    if (current_option < 0):

                        # Bottom of the list
                        current_option = len(options) - 1

                # Cursor down?
                elif (INPUT_SELECTION_DOWN in gameplay_input):

                    # Move down one
                    current_option += 1

                    # Wrap around?
                    if ( current_option >= len(options) ):

                        # To the top!
                        current_option = 0

                # Home key?
                elif (INPUT_SELECTION_HOME in gameplay_input):

                    # Top of the list
                    current_option = 0

                # End key?
                elif (INPUT_SELECTION_END in gameplay_input):

                    # End of the list
                    current_option = ( len(options) - 1 )

                # Page up?
                elif (INPUT_SELECTION_PAGEUP in gameplay_input):

                    # Let's move up by 2, that's about how many fit on a page
                    current_option -= 2

                    # Don't wrap
                    if (current_option < 0):

                        # Clamp
                        current_option = 0

                # Page down?
                elif (INPUT_SELECTION_PAGEDOWN in gameplay_input):

                    # Go down by 2, that's about how many fit on a page
                    current_option += 2

                    # Don't wrap
                    if ( current_option >= len(options) ):

                        # Clamp
                        current_option = ( len(options) - 1 )

                # Select current universe option?
                elif (INPUT_SELECTION_ACTIVATE in gameplay_input):

                    # Fade the app window, raising a special-case escape event when done.
                    #window_controller.fade_out(
                    #    on_complete = "universeselector:escape"
                    #)

                    # Lock future cursor movement as we fade out
                    self.cursor_locked = True


                    # We need to remember the title of the download so that we can add a newsfeeder item when the download finishes in a callback.
                    self.current_option_title = options[current_option].get_title()

                    # We also need to remember the size (in bytes) of the current option
                    self.current_option_size_in_bytes = options[current_option].get_size_in_bytes()


                    # Add a new progress tracking menu to the local menu controller
                    self.menu_controller.add(
                        control_center.get_widget_dispatcher().create_progress_menu().configure({
                            "title": control_center.get_localization_controller().get_label("download-begin:title"),
                            "message": options[current_option].get_title()
                        })
                    )


                    """
                    # Get a reference to the active menu (we'll only have one, the progress menu)
                    progress_menu = self.menu_controller.get_active_menu()

                    # Validate
                    if (progress_menu):

                        # Find the animated rectangle we use as a progress bar...
                        bar = progress_menu.get_active_page().find_widget_by_id("progress-bar")

                        # Validate
                        if (bar):

                            # For the progress bar to start at 0%
                            bar.configure({
                                "visible-width": 0
                            })

                            bar.visibility_controller.configure({
                                "interval": 0,
                                "target": 0
                            })
                    """


                    # Next, we will create a new batch request to retrieve all files associated with this DLC option.
                    control_center.get_http_request_controller().download_batch_with_name(
                        "batch-get-dlc-files",
                        None, # use default host
                        80,
                        options[current_option].get_files(),
                        max_requests = 5
                    )

                    logn( "dlc download", "Downloading files:\n%s\n" % "\n".join( [ "\t%s" % o for o in options[current_option].get_files() ] ) )

                    # Add a timer to periodically check the status of the batch download
                    self.timer_controller.add_repeating_event_with_name("listen-for-dlc-files", interval = 1, uses = -1, on_complete = "dlc:listen-for-dlc-files")


                    """
                    # Next, we should send a web request to fetch the info on what files we need to download for this level set
                    control_center.get_http_request_controller().send_get_with_name(
                        name = "get-file-listing",
                        host = None, # use default
                        port = 80,
                        url = options[current_option].get_files()#"/games/alrs/dlc/dlc.newdemo1.xml"
                    )


                    # Now let's add a timer event to listen for the response to that web request
                    self.timer_controller.add_repeating_event_with_name("listen-for-file-listing", interval = 1, uses = -1, on_complete = "dlc:listen-for-file-listing")
                    """


            # The scroll should always target the current option
            scroll_target = (current_option * OPTION_HEIGHT)


            # Need to scroll up?
            if (current_scroll > scroll_target):

                # Calculate ideal scroll pace
                dy = max(
                    20,
                    int( (current_scroll - scroll_target) / 10 )
                )

                # Scroll
                current_scroll -= dy


                # Don't overshoot
                if (current_scroll < scroll_target):

                    # Align
                    current_scroll = scroll_target

            # Need to scroll down?
            elif (current_scroll < scroll_target):

                # Calculate ideal scroll pace
                dy = max(
                    20,
                    int( (scroll_target - current_scroll) / 10 )
                )

                # Scroll
                current_scroll += dy


                # Don't overshoot
                if (current_scroll > scroll_target):

                    # Align
                    current_scroll = scroll_target



            # Let's process (alpha only, really) the backdrop widget
            backdrop_widget.process(control_center, None) # (?) No universe?

            # Go ahead and draw the backdrop widget, scrolling it off of the screen as we move down the list...
            backdrop_widget.draw(0, 0 - current_scroll, tilesheet_sprite, additional_sprites, text_renderer, window_controller)



            # Loop through each available option
            for i in range( 0, len(options) ):

                #print "%d - %s" % (i, options[i].name)
                #text_renderer.render_with_wrap( "%d - %s" % (i, options[i].name), 5, 5 + (i * text_renderer.font_height), (225, 225, 25))

                # Process the option (alpha / preview logic)
                #options[i].process()

                (sx, sy) = (
                    PAUSE_MENU_X + PREVIEW_PADDING,
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + (i * OPTION_HEIGHT) - (current_scroll)
                )

                scissor_controller.push( (sx, sy, 2 * PREVIEW_RADIUS, 2 * PREVIEW_RADIUS) )


                # Render the option centered on the screen
                options[i].draw_preview( sx + PREVIEW_RADIUS, sy + PREVIEW_RADIUS, tilesheet_sprite, additional_sprites, text_renderer, window_controller, active = (i == current_option) )

                scissor_controller.pop()


            for i in range( 0, len(options) ):

                (sx, sy) = (
                    PAUSE_MENU_X + PREVIEW_RADIUS + PREVIEW_PADDING,
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + (i * OPTION_HEIGHT) - (current_scroll)
                )

                indent = 0
                if ( i == current_option ):

                    indent = 10

                # If this is the current option (if and only if), then we shall render the title of the universe above the glow area.
                # We'll render it independent of scrolling action (just like the glow area), perhaps as an indicator that they can hit enter immediately??
                if (i == current_option):

                    # Yeah, I'm indenting by the font height.  I just want a little margin...
                    text_renderer.render_with_wrap( "\"%s\"" % options[i].get_title(), PAUSE_MENU_X + text_renderer.font_height, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2) - int(1.1 * text_renderer.font_height), (225, 225, 225) )
                    #options[i].draw_labels( indent + sx, sy + PREVIEW_RADIUS, text_renderer, window_controller, active = (i == current_option) )


                (sx, sy) = (
                    PAUSE_MENU_X + (2 * PREVIEW_RADIUS) + (2 * PREVIEW_PADDING),
                    int(SCREEN_HEIGHT / 2) - PREVIEW_RADIUS + (i * OPTION_HEIGHT) - (current_scroll)
                )

                options[i].draw_description_data( indent + sx, sy, PAUSE_MENU_WIDTH - ((2 * PREVIEW_RADIUS) + (2 * PREVIEW_PADDING)), (2 * PREVIEW_RADIUS), text_renderer, active = (i == current_option) )


            #text_renderer.render_with_wrap("Try to collect all of the gold in this story while avoiding all of the bad guys!", int(0.75 * SCREEN_WIDTH), int(SCREEN_HEIGHT / 2), (175, 175, 175), max_width = int(0.5 * SCREEN_WIDTH), align = "center")


            # ...
            window_controller.get_geometry_controller().draw_rect(PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), PAUSE_MENU_WIDTH, OPTION_HEIGHT, (225, 225, 225, 0.075))

            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), int(0.25 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.05), (225, 225, 225, 0.25) )
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X + int(0.25 * PAUSE_MENU_WIDTH), int(SCREEN_HEIGHT / 2) - int(OPTION_HEIGHT / 2), int(0.75 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.25), (225, 225, 225, 0.05) )

            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X, int(SCREEN_HEIGHT / 2) + int(OPTION_HEIGHT / 2) - 2, int(0.25 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.05), (225, 225, 225, 0.25) )
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient( PAUSE_MENU_X + int(0.25 * PAUSE_MENU_WIDTH), int(SCREEN_HEIGHT / 2) + int(OPTION_HEIGHT / 2) - 2, int(0.75 * PAUSE_MENU_WIDTH), 2, (225, 225, 225, 0.25), (225, 225, 225, 0.05) )


            # Render "tapering" effect
            #window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, 0, SCREEN_WIDTH, TAPER_AREA_SIZE, (0, 0, 0, 1.0), (0, 0, 0, 0.0))
            window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, (SCREEN_HEIGHT - TAPER_AREA_SIZE), SCREEN_WIDTH, TAPER_AREA_SIZE, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


            # Store events
            results = EventQueue()


            # Process local timer controller
            results.append(
                self.timer_controller.process()
            )


            # Process and draw local menus
            self.menu_controller.process(control_center, universe = None) # (?) No universe needed?
            self.menu_controller.draw(tilesheet_sprite, additional_sprites, text_renderer, window_controller)


            # Process window controller
            results.append(
                window_controller.process(control_center, None) # (?) no universe? ??? #some_universe) some_universe? ? ?
            )

            # Application-level fade control
            if ( window_controller.alpha_controller.get_interval() < 1.0 ):

                window_controller.render_fade_using_alpha_controller(
                    window_controller.fade_mode,
                    window_controller.alpha_controller
                )


            # Render the window controller's newsfeeder on top of even the fade effect
            window_controller.newsfeeder.draw(tilesheet_sprite, additional_sprites, text_renderer, window_controller)


            # Handle events
            event = results.fetch()

            # Loop all
            while (event):

                # Convenience
                action = event.get_action()


                # Special case - exit selector
                if ( action == "dlcselector:escape" ):

                    # Return the name of the universe selection we made
                    return options[current_option].get_name()

                # Special case - cancel selector
                elif ( action == "dlcselector:cancel" ):

                    # Return nothing, not that I think we care about return values from this selector anyway...
                    return None

                # Handle any other event normally
                else:

                    results.append(
                        self.handle_event(event, control_center)
                    )


                # Loop
                event = results.fetch()


            # Render newsfeeder items on top of even the fade effect
            #window_controller.newsfeeder.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], window_controller)


            # Show backbuffer
            pygame.display.flip()

            # Run sound controller processing (sound effects, background track looping, etc.)
            control_center.get_sound_controller().process(universe = None)


    # Handle an event (forward it)
    def handle_event(self, event, control_center):

        # Convenience
        action = event.get_action()


        if ( action == "dlc:get-file-listing" ):

            return self.handle_dlc_get_file_listing_event(event, control_center)

        elif ( action == "dlc:listen-for-file-listing" ):

            return self.handle_dlc_get_file_listing_event(event, control_center)

        elif ( action == "dlc:listen-for-dlc-files" ):

            return self.handle_listen_for_dlc_files_event(event, control_center)

        elif ( action == "dlc:clear-menu-controller" ):

            return self.handle_dlc_clear_menu_controller_event(event, control_center)


    # When we select a dlc option, we'll need to send a web request fo fetch the xml that defines
    # all of the files we need to download (and where on disk to save them).  After we get the structure data,
    # we'll create a batch request and download the files we need.
    def handle_dlc_get_file_listing_event(self, event, control_center):

        # We need to process the http request controller to poll for http data
        control_center.get_http_request_controller().process()

        # We want to peek to see if we have yet received the initial response to get the overall file listing.
        data = control_center.get_http_request_controller().peek_response_by_request_name("get-file-listing")

        # If the data is there, then the request has completed.
        if (data != None):

            # If we haven't yet created the batch request to get all of the necessary files, then we'll want to construct that right now.
            batch = control_center.get_http_request_controller().get_batch_by_name("batch-get-dlc-files")

            # Batch doesn't exist?  Create it...
            if (not batch):

                # Set up a list to hold the batch items
                batch_items = []


                # Compile the original web request response into an xml node
                node = XMLParser().create_node_from_xml(data)

                # See if we can find a base href
                base_href = ""

                # Validate
                if ( node.find_node_by_tag("base") ):

                    # Overwrite
                    base_href = node.find_node_by_tag("base").get_attribute("href")



                # Find the fileset node
                ref_fileset = node.find_node_by_tag("fileset")

                # Validate
                if (ref_fileset):

                    # I'm going to create a quick local function here (very rare!) to handle the recursion logic
                    def walk_node_for_files(node, base_href, base_path = ""):

                        # Store the files we find in a running list
                        files = []

                        # First we'll see if we have a folders node
                        ref_folders = node.get_first_node_by_tag("folders")

                        # Do we?
                        if (ref_folders):

                            # Check each folder
                            for ref_folder in ref_folders.get_nodes_by_tag("folder"):

                                # Step into the folder to get any files it might have; append results to our running list.
                                # Note that we add the given folder name to the active base path, in the process.
                                files.extend(
                                    walk_node_for_files( ref_folder, base_href, base_path = os.path.join(base_path, ref_folder.get_attribute("name") ) )
                                )


                        # Now check to see if we have any files in the node
                        ref_files = node.get_first_node_by_tag("files")

                        # Found some files?
                        if (ref_files):

                            # Loop through each file
                            for ref_file in ref_files.get_nodes_by_tag("file"):

                                # Add a file to the list of results, using a hash that indicates the path we'll save to and the url we'll download from.
                                # Also include the expected file size in bytes.
                                files.append({
                                    "path": os.path.join( base_path, ref_file.get_attribute("name") ),
                                    "url": "%s%s" % ( base_href, ref_file.get_attribute("src") ),
                                    "bytes": int( ref_file.get_attribute("bytes") ) # Cast as int
                                })


                        # Return the list of files we found (if any)
                        return files


                    # Now let's create a new batch request
                    control_center.get_http_request_controller().download_batch_with_name(
                        "batch-get-dlc-files",
                        None, # use default host
                        80,
                        walk_node_for_files(ref_fileset, base_href),
                        max_requests = 5
                    )


            # If the batch exists but is not yet completed, we'll update the progress bar
            elif ( not batch.is_completed() ):

                # Get a reference to the active menu (we'll only have one, the progress menu)
                progress_menu = self.menu_controller.get_active_menu()

                # Validate
                if (progress_menu):

                    # Find the animated rectangle we use as a progress bar...
                    bar = progress_menu.get_active_page().find_widget_by_id("progress-bar")

                    # Validate
                    if (bar):

                        # Update the progress percentage
                        bar.configure({
                            "visible-width": float( batch.get_bytes_downloaded() ) / float( self.current_option_size_in_bytes )
                        })

                    # Find the progress bar's label
                    label = progress_menu.get_active_page().find_widget_by_id("progress-bar-label")

                    # Validate
                    if (label):

                        # Set the text to the current download progress state
                        label.set_text( "Files:  %d / %d" % ( batch.get_files_downloaded(), batch.get_file_count() ) )

            # When we have finished downloading the batch, we'll confirm the download and such
            else:

                # Clear the "listen for files" timer; we've finished the download.
                self.timer_controller.remove_timer_by_name("listen-for-file-listing")

                # Hide the download progress bar page
                self.menu_controller.get_active_menu().get_active_page().hide()


                # With all downloading completed, let's officially end both the original file data web request
                # and also the batch request we created to get the actual file data.
                control_center.get_http_request_controller().end_request_by_name("get-file-listing")

                # End batch, too.
                control_center.get_http_request_controller().end_batch_by_name("batch-get-dlc-files")


                # After a moment, clear the menu controller.  This is pretty hacky.
                self.timer_controller.add_singular_event_with_name("clear-menu-controller", interval = 50, on_complete = "dlc:clear-menu-controller")


                # Post a newsfeeder item indicating that the download has completed
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": control_center.get_localization_controller().get_label("download-complete:title"),
                    "content": self.current_option_title
                })


        # No event to return
        return EventQueue()


    # After selecting an option, we send the web request for the structure data.  We need to listen for that at first.
    # Once we receive a response, we'll create a batch request to get all of the specified files.
    def handle_dlc_listen_for_file_listing_event(self, event, control_center):

        return EventQueue()


    # Listen for the batch download of all dlc files
    def handle_listen_for_dlc_files_event(self, event, control_center):

        # Events that might result from this callback
        results = EventQueue()


        # We need to process the http request controller to poll for http data
        control_center.get_http_request_controller().process()


        # Find batch object
        batch = control_center.get_http_request_controller().get_batch_by_name("batch-get-dlc-files")
        logn( "dlc download", "Listening for DLC files (%s)...\n" % batch )


        # Validate
        if (batch):

            # If batch is not complete, we'll update the progress bar
            if ( not batch.is_completed() ):
                logn( "dlc download", "\tNot completed...\n" )

                # Get a reference to the active menu (we'll only have one, the progress menu)
                progress_menu = self.menu_controller.get_active_menu()

                # Validate
                if (progress_menu):

                    # Find the animated rectangle we use as a progress bar...
                    bar = progress_menu.get_active_page().find_widget_by_id("progress-bar")

                    # Validate
                    if (bar):

                        # Update the progress percentage
                        bar.configure({
                            "visible-width": float( batch.get_bytes_downloaded() ) / float( batch.get_bytes_possible() )
                        })


                    # Calculate percent of download complete
                    percent = int(
                        float( batch.get_bytes_downloaded() ) / float( batch.get_bytes_possible() ) * 100.0
                    )
                    logn( "dlc download", "Bytes downloaded:  %s / %s\n" % ( batch.get_bytes_downloaded(), batch.get_bytes_possible() ))


                    # Find the progress bar's label
                    label = progress_menu.get_active_page().find_widget_by_id("progress-bar-label")

                    # Validate
                    if (label):

                        # Set the text to the current download progress state
                        label.set_text( "%s percent of %d file%s" % ( percent, batch.get_file_count(), ("s" if (batch.get_file_count() > 1) else "") ) )

            # Batch complete
            else:

                # End download process
                self.end_listen_for_dlc_files(control_center, control_center.get_localization_controller().get_label("download-complete:title"), self.current_option_title)

        # Not a valid batch
        else:

            # End with error
            self.end_listen_for_dlc_files(control_center, control_center.get_localization_controller().get_label("download-failed:title"), control_center.get_localization_controller().get_label("download-failed:message"))


        # Return results
        return results


    # Convenience function for cleaning up batch
    def end_listen_for_dlc_files(self, control_center, subject, message):

        # Clear the "listen for files" timer; we've finished the download.
        self.timer_controller.remove_timer_by_name("listen-for-dlc-files")

        # Hide the download progress bar page
        self.menu_controller.get_active_menu().get_active_page().hide()


        # With all downloading completed, let's officially end both the original file data web request
        # and also the batch request we created to get the actual file data.
        control_center.get_http_request_controller().end_request_by_name("get-file-listing")

        # End batch, too.
        control_center.get_http_request_controller().end_batch_by_name("batch-get-dlc-files")


        # After a moment, clear the menu controller.  This is pretty hacky.
        self.timer_controller.add_singular_event_with_name("clear-menu-controller", interval = 50, on_complete = "dlc:clear-menu-controller")


        # Post a newsfeeder item indicating that the download has completed
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GENERIC_ITEM,
            "title": subject, #"Download Complete!",
            "content": message #self.current_option_title
        })


        # Flag end of active download
        self.active_download_complete = True


    # Clear the local menu controller (i.e. after a download has completed) (i.e. totally lame hack job)
    def handle_dlc_clear_menu_controller_event(self, event, control_center):

        # Clear the menu controller
        self.menu_controller.clear()

        # Clear the cursor lock
        self.cursor_locked = False


        # No event to return
        return EventQueue()
