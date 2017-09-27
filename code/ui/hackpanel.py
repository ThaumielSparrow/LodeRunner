from code.render.glfunctions import draw_rect, draw_rounded_rect

from code.constants.common import HACK_PANEL_WIDTH, HACK_PANEL_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_ACTIVATE, HACK_PANEL_TEMPORARY_STATUS_DURATION

from code.controllers.intervalcontroller import IntervalController

class HackPanel:

    def __init__(self, passcode):

        # The code to unlock the terminal
        self.passcode = passcode

        # Currently entered code
        self.display = ""


        # Current cursor location
        self.cursor = 0


        # Status message
        self.status = "Awaiting input..."

        # Temporary status message (e.g. on incorrect input)
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
            (1, "1", 1), # value, label, width
            (2, "2", 1), 
            (3, "3", 1), 
            (4, "4", 1), 
            (5, "5", 1), 
            (6, "6", 1), 
            (7, "7", 1), 
            (8, "8", 1), 
            (9, "9", 1), 
            (-1, "Back", 1),
            (0, "0", 1),
            (-2, "Exit", 1)
        )


    # Fading away?
    def is_fading(self):

        return ( self.alpha__controller.get_target() == 0 )


    # Faded away?
    def is_gone(self):

        return ( not self.alpha_controller.is_visible() )

    def dismiss(self):

        self.alpha_controller.dismiss()


    def set_temporary_status(self, status):

        self.temporary_status = status
        self.temporary_status_interval = HACK_PANEL_TEMPORARY_STATUS_DURATION


    def process(self, user_input, session):

        # Process alpha
        self.alpha_controller.process()


        # Handle temporary status messages
        if (self.temporary_status_interval > 0):

            self.temporary_status_interval -= 1

            if (self.temporary_status_interval <= 0):
                self.temporary_status = ""


        per_row = 3


        # Check for user input
        if (INPUT_SELECTION_LEFT in user_input):

            if (self.cursor % per_row == 0):
                self.cursor += (per_row - 1)

            else:
                self.cursor -= 1


            if (self.cursor < 0):
                self.cursor += (per_row + 1)

        elif (INPUT_SELECTION_RIGHT in user_input):

            if ( (self.cursor + 1) % per_row == 0):
                self.cursor -= (per_row - 1)

            else:
                self.cursor += 1


            if (self.cursor >= len(self.buttons)):
                self.cursor -= per_row

        elif (INPUT_SELECTION_UP in user_input):

            self.cursor -= per_row

            if (self.cursor < 0):
                self.cursor += len(self.buttons)

        elif (INPUT_SELECTION_DOWN in user_input):

            self.cursor += per_row

            if (self.cursor >= len(self.buttons)):
                self.cursor -= len(self.buttons)

        elif (INPUT_SELECTION_ACTIVATE in user_input):

            # Append the value of the current selection
            (value, title, width) = self.buttons[self.cursor]

            if (value == -1):

                if (len(self.display) > 0):

                    # Backspace
                    self.display = self.display[0 : len(self.display) - 1]

            elif (value == -2):

                session["core.login-succeeded"]["value"] = "no"
                self.dismiss()

            else:

                self.display += "%d" % value

                # Same length as passcode?  Do check...
                if (len(self.display) == len(self.passcode)):

                    if (self.display == self.passcode):

                        session["core.login-succeeded"]["value"] = "yes"
                        self.dismiss()

                    else:

                        self.display = ""
                        self.set_temporary_status("Unauthorized Access Attempt")

    def render(self, text_renderer):

        # Lightbox effect
        draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (25, 25, 25, (self.alpha_controller.get_interval() / 1.5)))


        (x, y) = (
            int(SCREEN_WIDTH / 2) - int(HACK_PANEL_WIDTH / 2),
            int(SCREEN_HEIGHT / 2) - int(HACK_PANEL_HEIGHT / 2)
        )

        # Elegant background
        draw_rounded_rect(x, y, HACK_PANEL_WIDTH, HACK_PANEL_HEIGHT, (25, 25, 25, self.alpha_controller.get_interval()), (100, 50, 5, self.alpha_controller.get_interval()), border_size = 3)


        # general padding
        padding = 10


        # render point
        rx = padding
        ry = padding * 2


        # Render current entry status
        text_renderer.render("Enter Code:", x + rx + 15, y + ry, (225, 225, 225, self.alpha_controller.get_interval()))
        draw_rounded_rect(x + rx + (HACK_PANEL_WIDTH / 2) - 15, y + ry, (HACK_PANEL_WIDTH / 2) - (2 * padding), text_renderer.font_height, (25, 25, 25, self.alpha_controller.get_interval()), (70, 20, 5, self.alpha_controller.get_interval()))

        readout = self.display

        while (len(readout) < len(self.passcode)):
            readout += "?"

        readout_x = (x + HACK_PANEL_WIDTH - padding - text_renderer.size(readout) - 15 - padding)

        text_renderer.render(readout, readout_x, y + ry, (225, 225, 225, self.alpha_controller.get_interval()))
        text_renderer.render(self.display, readout_x, y + ry, (219, 183, 21, self.alpha_controller.get_interval()))


        # Advance cursor double space
        ry += 2 * text_renderer.font_height


        # Render all buttons
        per_row = 3
        row_width = 0

        button_width = int((HACK_PANEL_WIDTH - (2 * padding)) / 3)

        for i in range(0, len(self.buttons)):

            (value, title, width) = self.buttons[i]

            if (i == self.cursor):
                text_renderer.render(title, x + rx + int( (width * button_width) / 2) - int(text_renderer.size(title) / 2), y + ry, (219, 183, 21, self.alpha_controller.get_interval()))

                # Faint white highlight
                if (not self.is_fading()):
                    draw_rect(x + rx, y + ry, button_width, text_renderer.font_height, (225, 225, 225, 0.2))

            else:
                text_renderer.render(title, x + rx + int( (width * button_width) / 2) - int(text_renderer.size(title) / 2), y + ry, (225, 225, 225, self.alpha_controller.get_interval()))

            rx += (width * button_width)
            row_width += width

            if (row_width >= 3):

                row_width = 0

                rx = padding
                ry += text_renderer.font_height + padding

        # Double-space
        ry += text_renderer.font_height

        # Display status
        if (self.temporary_status != ""):

            text_renderer.render(self.temporary_status, x + int(HACK_PANEL_WIDTH / 2) - int(text_renderer.size(self.temporary_status) / 2), y + ry, (225, 25, 25, self.alpha_controller.get_interval()))

        else:

            text_renderer.render(self.status, x + int(HACK_PANEL_WIDTH / 2) - int(text_renderer.size(self.status) / 2), y + ry, (225, 225, 225, self.alpha_controller.get_interval()))
