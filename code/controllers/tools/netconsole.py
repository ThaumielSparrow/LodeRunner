from code.render.textblaster import TextBlaster

from code.utils.common import log

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.network import NET_CONSOLE_LINE_LIMIT, NET_CONSOLE_WIDTH, NET_CONSOLE_LINE_WIDTH, NET_CONSOLE_X, NET_CONSOLE_Y, NET_CONSOLE_LINE_LIFESPAN

from pygame.locals import K_BACKSPACE


class NetConsoleEntry:

    def __init__(self):

        # On / off
        self.status = STATUS_INACTIVE

        # Currently entered message
        self.buffer = ""


        # Optional delay.  Currently I use this to hackily avoid double-click style errors.
        self.delay = 5


    def toggle(self):

        if (self.status == STATUS_INACTIVE):

            self.status = STATUS_ACTIVE

            # Implicitly set delay (hack)
            self.delay = 5

        else:

            self.status = STATUS_INACTIVE


    def is_visible(self):

        return (self.status == STATUS_ACTIVE)


    def get_buffer(self):

        return self.buffer


    def clear(self):

        self.buffer = ""


    def process(self, system_input):

        # Delay period?
        if (self.delay > 0):

            # Wait
            self.delay -= 1

        # Ready to go
        else:

            if ( len(system_input["key-buffer"]) > 0 ):

                log( system_input["key-buffer"] )

                self.buffer += "%s" % system_input["key-buffer"][0]

            elif ( K_BACKSPACE in system_input["keydown-keycodes"] ):

                if ( len(self.buffer) > 0 ):

                    self.buffer = self.buffer[0 : (len(self.buffer) - 1)]


    def draw(self, x, y, window_controller):

        if ( self.is_visible() ):

            # Grab a reference to the text renderer
            text_renderer = window_controller.get_default_text_controller().get_text_renderer()


            # User instructions
            prompt_label = "Enter Message:"

            # Size of prompt
            prompt_label_size = text_renderer.size(prompt_label)

            # Padding after the prompt
            padding = 10


            # Render "Enter chat" type label
            text_renderer.render_with_wrap(prompt_label, x, y, (225, 225, 225, 0.75))


            # Now a background for the buffer
            window_controller.get_geometry_controller().draw_rounded_rect(x + prompt_label_size, y, NET_CONSOLE_WIDTH - (prompt_label_size + padding), 25, (25, 25, 25, 0.5), (225, 225, 225, 0.25))

            # Render current buffer
            text_renderer.render_with_wrap(self.buffer, x + (prompt_label_size + padding) + 5, y + 2, (225, 225, 225, 0.75))


class NetConsoleLine:

    def __init__(self, text, text_type = None):

        # Line status
        self.status = STATUS_ACTIVE

        # Original text
        self.text = text

        # Optional type
        self.text_type = text_type


        # Padding within frame
        (self.padding_x, self.padding_y) = (
            10,
            5
        )


        # Create a text blaster to control fade in / out behavior
        self.text_blaster = TextBlaster(self.text, max_width = NET_CONSOLE_LINE_WIDTH, letters_per = 5, effect = "blaster:line-by-line", duration = 50, lag = 2, repeat_threshold = 50)

        # We will have to set up the text blaster on the first rendering pass
        self.is_text_blaster_ready = False


        # A line will appear for a set duration of time before going away
        self.lifespan = NET_CONSOLE_LINE_LIFESPAN


    def get_text(self):

        return self.text


    def is_active(self):

        return (self.status == STATUS_ACTIVE)


    # Check to see if this line has a given text type (class)
    def has_class(self, text_type):

        # Check to see if we set class
        if (self.text_type != None):

            # Get all classes for this line
            classes = self.text_type.split(",")

            # Loop each
            for s in classes:

                # Check match
                if ( s.strip() == text_type ):

                    # Found match
                    return True


        # Does not have class
        return False


    def get_render_height(self, text_renderer):

        return (2 * self.padding_y) + (text_renderer.font_height * text_renderer.wrap_lines_needed( self.get_text(), max_width = (NET_CONSOLE_LINE_WIDTH - (2 * self.padding_x)) ))


    def process(self):

        # Process text blaster
        self.text_blaster.process()


        # Decrease lifespan, etc.
        if (self.lifespan > 0):

            self.lifespan -= 1

            # When we reach 0, we want to set the line to fade away...
            if (self.lifespan <= 0):

                # Goodbye
                self.text_blaster.dismiss()

        # If the lifespan has ended, let's check to see if the text blaster has finished its fade...
        else:

            if ( self.text_blaster.is_complete() ):

                # Mark this line for removal
                self.status = STATUS_INACTIVE


    def draw(self, x, y, window_controller):

        # Grab text renderer
        text_renderer = window_controller.get_default_text_controller().get_text_renderer()

        # If our text blaster isn't ready, then we need to initialize the fade values (so they fade in)
        if (not self.is_text_blaster_ready):

            self.text_blaster.setup_initial_fade_values(text_renderer)

            # Ready!
            self.is_text_blaster_ready = True


        # Default color codes
        color_codes = {
            "special": (225, 25, 25)
        }

        # Retrieve generic css properties for the "chatline" selector (used only for these chatlines)
        properties = window_controller.get_css_controller().get_properties("chatline")

        # Check for color codes
        if ( "bbcode" in properties ):

            # Update default color codes
            color_codes.update( properties["bbcode"] )


        # How much vertical screen estate do we need for this line?
        h = (2 * self.padding_y) + text_renderer.font_height * text_renderer.wrap_lines_needed(self.get_text(), max_width = ( NET_CONSOLE_LINE_WIDTH - (2 * self.padding_x)) )

        # Render backdrop
        window_controller.get_geometry_controller().draw_rounded_rect(x, y, NET_CONSOLE_LINE_WIDTH, h, (20, 20, 20, 0.5), border = (225, 225, 225, 0.2))#(20, 20, 20, 0.25), (45, 45, 45, 0.25), border = (225, 225, 225, 0.5))

        height_used = (
            (2 * self.padding_y) +
            text_renderer.render_with_wrap(
                self.get_text(),
                self.padding_x + x,
                self.padding_y + y,
                (225, 225, 225, 0.5),
                letter_fade_percentages = self.text_blaster.get_letter_fade_values(),
                max_width = ( NET_CONSOLE_LINE_WIDTH - (2 * self.padding_x)),
                color_classes = color_codes
            )
        )

        return height_used


class NetConsole:

    def __init__(self):

        # Keep a queue of the lines of text to show (commands, chatlines, server notices, etc.)
        self.queue = []

        # How long will we wait before removing the oldest message?
        self.timer = 0


        # Whenever we commit a change to the queue (addition or removal), we'll want to update
        # how much space we need to render each and every line (accounting for wordwrap and all that)
        self.cumulative_render_height = None


        # Padding values
        self.padding_x = 15
        self.padding_y = 5

        # Margin value
        self.margin_y = 10


        # When the top active message times out, it will disappear, and the lower lines will slide up...
        self.slide_offset = 0
        self.slide_offset_target = 0

        self.slide_speed_up = 0.25

        # Callback for when a slide concludes
        self.on_slide_complete = None


    # Add a new line to the console
    def add(self, text, text_type = None):

        # Create a new queue item
        self.queue.append(
            NetConsoleLine(text, text_type)
        )

        # Limit the number of lines that can appear at a given time
        while ( len(self.queue) > NET_CONSOLE_LINE_LIMIT ):

            self.queue.pop(0)


        # Set the raw line count to None to prompt the object to recalculate the total on the next pass
        self.cumulative_render_height = None


    # Remove all lines having a given class type
    def remove_lines_by_class(self, text_type):

        # Check each line
        i = 0
        while ( i < len(self.queue) ):

            # Has class?
            if ( self.queue[i].has_class(text_type) ):

                # Remove it
                self.queue.pop(i)

            # Keep it and loop forward
            else:
                i += 1


    # Set a new slide value on the console, after which the lines will slide to the top of the console...
    def set_slide_offset(self, offset, f_on_slide_complete = None):

        self.slide_offset = offset
        self.slide_offset_target = 0

        self.on_slide_complete = f_on_slide_complete


    # Get widget height
    def get_height(self, window_controller):

        # Grab text renderer
        text_renderer = window_controller.get_default_text_controller().get_text_renderer()

        # Do we need to calculate the raw line height of this console?
        if (self.cumulative_render_height == None):

            self.cumulative_render_height = sum( (self.margin_y + o.get_render_height(text_renderer)) for o in self.queue ) - (0 * self.margin_y)

        # Return cumulative height
        return self.cumulative_render_height


    def process(self):

        # Do we have any slide data to process?
        if (self.slide_offset > self.slide_offset_target):

            self.slide_offset -= self.slide_speed_up

            # Don't overshoot
            if (self.slide_offset <= self.slide_offset_target):

                self.slide_offset = self.slide_offset_target

                # Callback defined?
                if (self.on_slide_complete):

                    self.on_slide_complete()

                    # Reset callback reference
                    self.on_slide_complete = None


        # Process any queue item
        i = 0
        while ( i < len(self.queue) ):

            # Process line
            self.queue[i].process()


            # Line is still active?
            if ( self.queue[i].is_active() ):

                i += 1

            # No; let's remove it
            else:

                self.queue.pop(i)

                # Reset our render height tracking as the content length has changed...
                self.cumulative_render_height = None


    def draw(self, x, y, window_controller):

        # Grab text renderer
        text_renderer = window_controller.get_default_text_controller().get_text_renderer()


        # Padding values
        (padding_x, padding_y) = (self.padding_x, self.padding_y)

        # Margin value
        margin_y = self.margin_y


        # Make sure height is up to date
        self.cumulative_render_height = self.get_height(window_controller)


        # Default render point
        (rx, ry) = (
            x + padding_x,
            y + padding_y
        )

        # Backdrop dimensions
        (w, h) = (
            NET_CONSOLE_WIDTH,
            self.cumulative_render_height
        )

        # Proper backdrop
        #window_controller.get_geometry_controller().draw_rect(0, 480 - h, 640, h, (20, 20, 20, 0.5))#(20, 20, 20, 0.25), (45, 45, 45, 0.25), border = (225, 225, 225, 0.5))
        #window_controller.get_geometry_controller().draw_rect(0, 480 - h, 640, 2, (125, 125, 125, 0.25))#(20, 20, 20, 0.25), (45, 45, 45, 0.25), border = (225, 225, 225, 0.5))


        # Render the text of each line...
        for line in self.queue:

            ry += line.draw(rx, ry, window_controller)

            ry += margin_y


        # Return how much height we used
        return h
