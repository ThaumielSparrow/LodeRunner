from common import UIWidget

from code.tools.xml import XMLParser, XMLNode
from code.utils.common import log, xml_encode, xml_decode, set_alpha_for_rgb

from code.controllers.intervalcontroller import IntervalController

from code.utils.common import log, log2

from pygame.locals import *

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_ACTIVATE, PROMPT_PANEL_TEMPORARY_STATUS_DURATION

class Keyboard(UIWidget):

    def __init__(self):

        UIWidget.__init__(self, selector = "keyboard")

        self.state_changed = False


        # Track whether or not the user last used the alphanumeric keys on their physical keyboard to
        # update the entered value.  When so, we'll treat "enter" keypress as an automatic submission (instead of "selecting" the active character).
        self.last_entry_used_explicit_keydown = False

        # Sometimes we enact a delay period during which we'll ignore all keyboard input.
        # I'm doing this mostly to avoid "double-click" situations.
        self.delay = 5


        # What prompt should this keyboard display?  (e.g. "Enter value for [some task]")
        self.prompt = "Enter a Title for Your Save Game:" # Lame default


        # Currently entered text
        self.value = ""


        # Minimum length (optional)
        self.min_length = 0

        # Maximum display length
        self.max_length = 32 # Hard-coded default


        # Current cursor location
        self.cursor = 0


        # Buttons per row
        self.per_row = 10 # hard-coded default

        # Padding between buttons
        self.button_padding = 10


        # Custom horizontal alignment
        self.halign = "left" # left, center, bottom

        # Custom vertical alignment
        self.valign = "top" # top, center, bottom


        # Events
        self.on_save = ""
        self.on_cancel = ""


        # Did we save, or did we cancel?
        self.is_saved = False


        # Status message
        self.status = "Awaiting input..."

        # Temporary status message (e.g. on incorrect or invalid input)
        self.temporary_status = ""
        self.temporary_status_interval = 0


        # Alpha control
        self.alpha_controller = IntervalController(
            interval = 0.0,
            target = 1.0,
            speed_in = 0.015,
            speed_out = 0.035
        )


        # The buttons
        self.buttons = (
            ("1", "[color=numeric]1[/color]", 1), # value, label, width
            ("2", "[color=numeric]2[/color]", 1),
            ("3", "[color=numeric]3[/color]", 1),
            ("4", "[color=numeric]4[/color]", 1),
            ("5", "[color=numeric]5[/color]", 1),
            ("6", "[color=numeric]6[/color]", 1),
            ("7", "[color=numeric]7[/color]", 1),
            ("8", "[color=numeric]8[/color]", 1),
            ("9", "[color=numeric]9[/color]", 1),
            ("0", "[color=numeric]0[/color]", 1),
            ("A", "A", 1),
            ("B", "B", 1),
            ("C", "C", 1),
            ("D", "D", 1),
            ("E", "E", 1),
            ("F", "F", 1),
            ("G", "G", 1),
            ("H", "H", 1),
            ("I", "I", 1),
            ("J", "J", 1),
            ("K", "K", 1),
            ("L", "L", 1),
            ("M", "M", 1),
            ("N", "N", 1),
            ("O", "O", 1),
            ("P", "P", 1),
            ("Q", "Q", 1),
            ("R", "R", 1),
            ("S", "S", 1),
            ("T", "T", 1),
            ("U", "U", 1),
            ("V", "V", 1),
            ("W", "W", 1),
            ("X", "X", 1),
            ("Y", "Y", 1),
            ("Z", "Z", 1),
            (" ", "[color=nonalphanumeric]Space[/color]", 1),
            (-1, "[color=nonalphanumeric]Del[/color]", 1),
            (-3, "[color=nonalphanumeric]Cancel[/color]", 1),
            (-2, "[color=nonalphanumeric]Enter[/color]", 1)
        )


    def configure(self, options):

        # Standard UIWidget configuration
        UIWidget.configure(self, options)


        # Additional keyboard-specific configuration options
        if ( "prompt" in options ):
            self.prompt = options["prompt"]

        if ( "text" in options ):
            self.value = options["text"]

        if ( "min-length" in options ):
            self.min_length = int( options["min-length"] )

        if ( "max-length" in options ):
            self.max_length = int( options["max-length"] )

        if ( "value" in options ):
            self.value = options["value"]

        if ( "per-row" in options ):
            self.per_row = int( options["per-row"] )

        if ( "button-padding" in options ):
            self.button_padding = int( options["button-padding"] )

        if ( "halign" in options ):
            self.halign = options["halign"]

        if ( "valign" in options ):
            self.valign = options["valign"]

        if ( "save-params" in options ):
            self.on_save_params = options["save-params"]

        if ( "cancel-params" in options ):
            self.on_cancel_params = options["cancel-params"]

        if ( "on-save" in options ):
            self.on_save = options["on-save"]

        if ( "on-cancel" in options ):
            self.on_cancel = options["on-cancel"]


        # For chaining
        return self


    # Save Keyboard state
    def save_state(self):

        # Standard UIWidget state
        root = UIWidget.save_state(self)


        # Add in a few state details specific to this Keyboard
        details_node = root.add_node(
            XMLNode("keyboard")
        )

        # Save cursor location.
        # I believe we no longer use slide-interval / -target; presumably
        # legacy code I never removed?  (load_state makes no reference to it...)
        details_node.set_attributes({
            "cursor.y": self.cursor,
            "slide-interval": 0, # self.slide_interval,
            "slide-interval-target": 0 #self.slide_interval_target
        })


        # Return node
        return root


    # Load Keyboard state
    def load_state(self, node):

        # Standard UIWidget state
        UIWidget.load_state(self, node)


        # Grab details specific to this RowMenu
        details_node = node.find_node_by_tag("rowmenu")

        # Validate
        if (details_node):

            # Restore cursor
            self.cursor = int( details_node.get_attribute("cursor.y") )


    def save_state_as_xml(self):

        xml = """
            <cursor y = '%d' />
        """ % self.cursor

        return xml


    def load_state_from_xml(self, xml):

        # Generic node
        node = XMLParser().create_node_from_xml(xml)

        ref_item = node.get_first_node_by_tag("item")

        if (ref_item):

            # Load the cursor data
            ref_cursor = ref_item.get_first_node_by_tag("cursor")

            if (ref_cursor):

                self.cursor = int( ref_cursor.get_attribute("y") )


    # Overwrite the standard translate call
    # to peek into the translations for prompt and default.
    def translate(self, h):

        # Standard translation logic
        UIWidget.translate(self, h)

        """
        # Check for "prompt"
        if ( "prompt" in h ):

            # Configure
            self.configure({
                "prompt": h["prompt"]
            })

        # Check for default value
        if ( "value" in h ):

            # Configure
            self.configure({
                "value": h["value"]
            })
        """


    # Fading away?
    def is_fading(self):

        return ( self.alpha_controller.get_interval() == 0 )


    # Faded away?
    def is_gone(self):

        return ( not self.alpha_controller.is_visible() )


    def report_widget_height(self, text_renderer):

        # Start with padding
        height = self.button_padding * 2

        # Count rows
        rows = int( (len(self.buttons) + (self.per_row - 1)) / self.per_row )

        # Add height of each row
        height += ( (text_renderer.font_height + self.button_padding) * rows )

        # Bottom padding
        height += self.button_padding

        # Double-space before temporary status readout
        height += text_renderer.font_height

        # Account for readout as well
        height += text_renderer.font_height


        # Finally...
        return height


    # Get current value
    def get_value(self):

        return self.value


    # Validate (for length only, currently)
    def validate(self):

        # Get entered value
        s = self.value.strip()


        # Too short?
        if ( len(s) < self.min_length ):

            # Set error message
            self.set_temporary_status("Minimum of %s character(s)" % self.min_length)

            # Fail
            return False

        # Too long?
        elif ( len(s) > self.max_length ):

            # Set error message
            self.set_temporary_status("Maximum of %s character(s)" % self.max_length)

            # Fail
            return False

        # Success!
        else:

            return True


    def set_temporary_status(self, status):

        self.temporary_status = status
        self.temporary_status_interval = PROMPT_PANEL_TEMPORARY_STATUS_DURATION


    def append_to_display(self, value):

        self.value += value

        # Same length as passcode?  Do check...
        if (len(self.value) > self.max_length):

            self.value = self.value[0 : self.max_length]

            self.set_temporary_status("Character Limit Reached!")


    def process(self, control_center, universe):#user_input, raw_keyboard_input, network_controller, universe = None, session = None, save_controller = None):

        # Common widget processing
        results = self.__std_process__(control_center, universe)


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # Fetch the gameplay input and use it as user input
        user_input = input_controller.get_gameplay_input()

        # Fetch touched keys to use as raw keyboard input
        touched_keys = input_controller.get_touched_keys()


        # Process alpha
        results.append(
            self.alpha_controller.process()
        )


        # Handle temporary status messages
        if (self.temporary_status_interval > 0):

            self.temporary_status_interval -= 1

            if (self.temporary_status_interval <= 0):
                self.temporary_status = ""


        # Do we have to process a delay period?
        if (self.delay > 0):

            # Wait...
            self.delay -= 1

        # If not, let's check input...
        else:

            # Check for user input
            if (INPUT_SELECTION_LEFT in user_input):

                if (self.cursor % self.per_row == 0):
                    self.cursor += (self.per_row - 1)

                else:
                    self.cursor -= 1


                if (self.cursor < 0):
                    self.cursor += (self.per_row + 1)

                # Reset the "explicit keydown" tracker
                self.last_entry_used_explicit_keydown = False

            elif (INPUT_SELECTION_RIGHT in user_input):

                if ( (self.cursor + 1) % self.per_row == 0):
                    self.cursor -= (self.per_row - 1)

                else:
                    self.cursor += 1


                if (self.cursor >= len(self.buttons)):
                    self.cursor -= self.per_row

                # Reset the "explicit keydown" tracker
                self.last_entry_used_explicit_keydown = False

            elif (INPUT_SELECTION_UP in user_input):

                self.cursor -= self.per_row

                if (self.cursor < 0):
                    self.cursor += len(self.buttons)

                # Reset the "explicit keydown" tracker
                self.last_entry_used_explicit_keydown = False

            elif (INPUT_SELECTION_DOWN in user_input):

                self.cursor += self.per_row

                if (self.cursor >= len(self.buttons)):
                    self.cursor -= len(self.buttons)

                # Reset the "explicit keydown" tracker
                self.last_entry_used_explicit_keydown = False

            elif (INPUT_SELECTION_ACTIVATE in user_input):

                # If the user last used explicit keyboard input, then we're going to assume they
                # are pressing enter to submit the data.
                if (self.last_entry_used_explicit_keydown):

                    # Validate entered value
                    if ( self.validate() ):

                        # Submit
                        results.add(
                            action = self.on_save,
                            params = {
                                "widget": self
                            }
                        )

                        # Reset the "explicit keydown" tracker
                        self.last_entry_used_explicit_keydown = False

                else:

                    # Append the value of the current selection
                    (value, title, width) = self.buttons[self.cursor]

                    # Backspace
                    if (value == -1):

                        if (len(self.value) > 0):

                            # Backspace
                            self.value = self.value[0 : len(self.value) - 1]

                    # Submit
                    elif (value == -2):

                        # Validate entered data
                        if ( self.validate() ):

                            #self.dismiss()

                            results.add(
                                action = self.on_save,
                                params = {
                                    "widget": self
                                }
                            )
                            #return self.on_save_params

                    # Cancel
                    elif (value == -3):

                        #self.dismiss()

                        results.add(
                            action = self.on_cancel,
                            params = {
                                "widget": self
                            }
                        )
                        #return self.on_cancel_params

                    # Character value
                    else:

                        self.append_to_display(value)

            # In the absence of any other input, we'll check some raw keyboard input scenarios...
            else:

                # Backspace?
                if (K_BACKSPACE in touched_keys):

                    self.value = self.value[0: len(self.value) - 1]

                # Enter?
                #elif (K_RETURN in touched_keys):
                #    return self.on_save_params

                # Cancel?
                elif (K_ESCAPE in touched_keys):

                    #self.dismiss()

                    results.add(
                        action = self.on_cancel,
                        params = {
                            "widget": self
                        }
                    )
                    #return self.on_cancel_params

                # None of the above?  We can check for alphanumeric input, then...
                else:

                    for keycode in range(K_0, K_9 + 1) + range(K_a, K_z + 1) + [K_SPACE]:

                        if (keycode in touched_keys):

                            # Translate keycode-to-character
                            character = chr(keycode).upper()

                            # Append to display
                            self.append_to_display(character)

                            # Update cursor location...
                            for i in range(0, len(self.buttons)):

                                if (self.buttons[i][0] == character):

                                    self.cursor = i


                            # Track that the user explicitly pressed an alphanumeric key.  At this point, if they
                            # hit enter (without any cursor movement), we should submit the keyboard ("smartly").
                            self.last_entry_used_explicit_keydown = True


        # Return events
        return results


    def draw(self, sx, sy, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Rendering position
        (rx, ry) = (
            sx + self.get_x() + self.get_padding_left() + self.hslide_controller.get_interval(),
            sy + self.get_y() + self.get_padding_top() + self.vslide_controller.get_interval()
        )

        # Dimensions
        (width, height) = (
            self.get_width(),
            self.get_render_height(text_renderer)
        )


        # Horizontal alignment checks
        if (self.halign == "center"):

            rx -= int(width / 2)

        elif (self.halign == "right"):

            rx -= width


        # Vertical alignment checks
        if (self.valign == "center"):

            ry -= int(height / 2)

        elif (self.valign == "bottom"):

            ry -= height


        alpha = self.alpha_controller.get_interval()
        alpha_factor = self.get_background_alpha()


        # Does this keyboard use a lightbox effect?
        if (self.uses_lightbox):

            # Render the lightbox as a percentage of the current alpha value
            window_controller.get_geometry_controller().draw_rect( 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, (DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE * alpha)) )


        # Now, render the border, if/a
        if (self.render_border):

            self.__std_render_border__(rx, ry - self.get_padding_top(), width, height, window_controller)



        # render point
        (cx, cy) = (
            rx + self.button_padding,
            ry + (self.button_padding * 2)
        )


        # Render current entry status
        text_renderer.render( self.prompt, cx + 15, cy, set_alpha_for_rgb(alpha * alpha_factor, self.get_color()) )

        window_controller.get_geometry_controller().draw_rounded_rect(
            cx + int(self.get_width() / 2) - 15,
            cy,
            int(self.get_width() / 2) - (2 * self.button_padding),
            text_renderer.font_height,
            set_alpha_for_rgb( alpha_factor * self.alpha_controller.get_interval(), self.get_gradient_start() ),
            set_alpha_for_rgb( alpha_factor * self.alpha_controller.get_interval(), self.get_border_color() )
        )

        readout = self.value

        #while (len(readout) < len(self.passcode)):
        #    readout += "?"

        readout_x = (self.get_width() - self.button_padding - text_renderer.size(readout) - 15 - self.button_padding)

        text_renderer.render(readout, readout_x, cy, set_alpha_for_rgb(alpha_factor * self.alpha_controller.get_interval(), self.get_color()))
        text_renderer.render(self.value, readout_x, cy, set_alpha_for_rgb(alpha_factor * self.alpha_controller.get_interval(), self.get_color()))


        # Advance cursor double space
        cy += 2 * text_renderer.font_height


        # Track width uses in row so far
        row_width = 0

        # Calculate width of each button
        button_width = int( (self.get_width() - (2 * self.button_padding)) / self.per_row )

        for i in range(0, len(self.buttons)):

            (value, title, width) = self.buttons[i]

            if (i == self.cursor):
                text_renderer.render_with_wrap(title, cx + int( (width * button_width) / 2) - int(text_renderer.size(title) / 2), cy, set_alpha_for_rgb(self.alpha_controller.get_interval(), self.get_color()), color_classes = self.get_bbcode())

                # Faint white highlight
                if (not self.is_fading()):
                    window_controller.get_geometry_controller().draw_rect(cx, cy, button_width, text_renderer.font_height, set_alpha_for_rgb(0.2, self.get_color()))

            else:
                text_renderer.render_with_wrap(title, cx + int( (width * button_width) / 2) - int(text_renderer.size(title) / 2), cy, set_alpha_for_rgb(self.alpha_controller.get_interval(), self.get_color()), color_classes = self.get_bbcode())

            cx += (width * button_width)
            row_width += width

            if (row_width >= self.per_row):

                row_width = 0

                cx = rx + self.button_padding
                cy += text_renderer.font_height + self.button_padding

        # Double-space
        cy += text_renderer.font_height

        # Display status
        if (self.temporary_status != ""):

            text_renderer.render(self.temporary_status, rx + int(self.get_width() / 2) - int(text_renderer.size(self.temporary_status) / 2), cy, (225, 25, 25, alpha))

        else:

            text_renderer.render(self.status, rx + int(self.get_width() / 2) - int(text_renderer.size(self.status) / 2), cy, (225, 225, 225, alpha))

