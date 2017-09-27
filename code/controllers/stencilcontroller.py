from code.render.glfunctions import stencil_enable, stencil_disable, stencil_enable_painting, stencil_enable_erasing, stencil_enforce_painted_only, stencil_enforce_unpainted_only, stencil_clear_region, stencil_clear

from code.constants.common import STENCIL_MODE_NONE, STENCIL_MODE_PAINT, STENCIL_MODE_ERASE, STENCIL_MODE_PAINTED_ONLY, STENCIL_MODE_UNPAINTED_ONLY

class StencilController:

    def __init__(self):

        # What mode are we using?
        self.stencil_mode = STENCIL_MODE_NONE

        # Locking the scissor controller prevents changing mode
        self.lock_count = 0


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



    def set_mode(self, mode):

        if ( not self.is_locked() ):

            self.stencil_mode = mode


            # No stencil testing / painting
            if (mode == STENCIL_MODE_NONE):

                # Disable stencil buffer
                stencil_disable()

            # Free to paint anywhere on screen; stencil buffer will remember everything
            elif (mode == STENCIL_MODE_PAINT):

                # Enable stencil buffer (so that it can remember our painting)
                stencil_enable()

                # Set it to accept all painting
                stencil_enable_painting()

            # Free to paint anywhere on screen, but erase the stencil buffer (mark as unpainted) wherever we're painting
            elif (mode == STENCIL_MODE_ERASE):

                # Enable stencil buffer
                stencil_enable()

                # Set it to erase previously painted areas that we now draw over
                stencil_enable_erasing()

            # Only free to paint on previously-painted areas
            elif (mode == STENCIL_MODE_PAINTED_ONLY):

                # Make sure stencil is on
                stencil_enable()

                # Enforce
                stencil_enforce_painted_only()

            elif (mode == STENCIL_MODE_UNPAINTED_ONLY):

                # Make sure stencil is on
                stencil_enable()

                # Enforce
                stencil_enforce_unpainted_only()


    def get_mode(self):

        return self.stencil_mode


    def clear_region(self, x, y, w, h):

        if ( not self.is_locked() ):

            stencil_clear_region(x, y, w, h)


    def clear(self):

        if ( not self.is_locked() ):

            stencil_enable()

            stencil_clear()
