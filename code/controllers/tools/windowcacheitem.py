from code.render.glfunctions import delete_texture

from code.utils.common import log, log2

# A container to house data on "cached" framebuffer regions (e.g. cached text blocks)
class WindowCacheItem:

    def __init__(self, texture_id, texture_size, about = ""):

        # When we create the cache, we'll want to track the texture id
        self.texture_id = texture_id

        # We'll need to track the ultimate size of the texture...
        self.texture_size = texture_size


        # **debug
        self.about = about


        log( "welcome to new cache item:\n\ttext:  %s" % self.about[0:70] )


    def __del__(self):

        log( "say goodbye to cache item:\n\ttext:  %s" % self.about[0:70] )

        # Texture to delete?
        if (self.texture_id != None):

            # Free the texture
            delete_texture(self.texture_id)

            # Safety
            self.texture_id = None


    # Get texture id
    def get_texture_id(self):

        return self.texture_id


    # Get texture size
    def get_texture_size(self):

        return self.texture_size
