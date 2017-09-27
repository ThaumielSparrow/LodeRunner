from code.render.glfunctions import *

from code.utils.common import offset_rect

class ScissorController:

    def __init__(self, render_width, render_height, screen_width, screen_height):

        # Unlikely that we get carried away with this, but keep a stack of scissor test regions.
        # We'll default to full screen (or "viewable area" when we have resolution to spare)
        # when the stack is empty.
        self.stack = []

        # Locking the scissor controller prevents push/pop operations
        self.lock_count = 0


        # Reference the overall screen width / height we established at application launch
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Reference the render region (in case we needed a higher resolution (with extra space) for video card compatibility)
        self.render_width = render_width
        self.render_height = render_height


    # Enable scissor test
    def enable(self):

        #return
        scissor_on()


    # Disable scissor test
    def disable(self):

        scissor_off()


    # Lock the controller
    def lock(self):

        self.lock_count += 1


    # Unlock the controller
    def unlock(self):

        self.lock_count -= 1

        # Keep it non-negative...
        if (self.lock_count < 0):
            self.lock_count = 0


    # Check lock status
    def is_locked(self):

        return (self.lock_count > 0)


    # Add a new scissor test
    def push(self, r):

        if ( not self.is_locked() ):

            self.stack.append(
                offset_rect(
                    r,
                    x = int( (self.render_width - self.screen_width) / 2),
                    y = int( (self.render_height - self.screen_height) / 2)
                )
            )

            self.set_scissor( self.stack[-1] )


    # Clear the last scissor test
    def pop(self):

        result = None

        if ( not self.is_locked() ):

            # Remove last if we have one
            if ( len(self.stack) > 0 ):

                result = self.stack.pop()


            # A new if; can we revert to a previous scissor?
            if ( len(self.stack) > 0 ):

                self.set_scissor( self.stack[-1] )

            # If not, then let's just use the entire renderable area
            else:

                self.set_scissor( (0, 0, self.render_width, self.render_height) )

        return result


    # Configure the gl scissor test
    def set_scissor(self, r):

        if (r):
            #set_scissor( ((self.render_width - self.screen_width) / 2) + r[0], ((self.render_height - self.screen_height) / 2) + (self.screen_height - r[1] - r[3]), r[2], r[3] )
            set_scissor( r[0], (self.render_height - r[1] - r[3]), r[2], r[3] )

        else:
            set_scissor( (self.render_width - self.screen_width) / 2, ((self.render_height - self.screen_height) / 2), self.screen_width, self.screen_height)


    # Pause scissor test
    def pause(self):

        # If unlocked!
        if ( not self.is_locked() ):

            # Simple disable call
            scissor_off()


    # Force pause - even when locked!  Use carefully!
    def force_pause(self):

        # Disable scissor test
        scissor_off()


    # Resume scissor test - this is the same thing as enabling... just an alias I guess
    def resume(self):

        # Make sure we're not locked...
        if ( not self.is_locked() ):

            # Simple enable
            scissor_on()
