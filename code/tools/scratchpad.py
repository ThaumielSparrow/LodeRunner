from code.render.glfunctions import create_scratch_pad, activate_scratch_pad, delete_scratch_pad, delete_texture

from code.utils.common import log, log2


# Scratch pads are offscreen frame buffer (textures) that we can render to.
# They can be larger than the game's base resolution.
class ScratchPad:

    def __init__(self, width, height):

        # Remember dimensions
        self.width = width
        self.height = height

        # Create a framebuffer for this pad
        self.buffer_id = create_scratch_pad()

        # Create (and retrieve) the texture we'll associate with this pad
        self.texture_id = activate_scratch_pad(self.buffer_id, self.width, self.height)


    # Deconstructor
    def __del__(self):
        return


    # Release texture and framebuffer
    def unload(self):

        # Delete the associated texture
        delete_texture(self.texture_id)

        # Delete the framebuffer
        delete_scratch_pad(self.buffer_id)


    # Get width
    def get_width(self):

        return self.width


    # Get height
    def get_height(self):

        return self.height


    # Get frame buffer id
    def get_buffer_id(self):

        return self.buffer_id


    # Get texture target id
    def get_texture_id(self):

        return self.texture_id

