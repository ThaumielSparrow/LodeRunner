import os
import random

from tools.windowcacheitem import WindowCacheItem

from code.extensions.common import HookableExt

from code.controllers.intervalcontroller import IntervalController
from code.controllers.scissorcontroller import ScissorController
from code.controllers.stencilcontroller import StencilController
from code.controllers.geometrycontroller import GeometryController
from code.controllers.gfxcontroller import GfxController
from code.controllers.textcontroller import TextController
from code.controllers.csscontroller import CSSController

from code.tools.eventqueue import EventQueue
from code.tools.scratchpad import ScratchPad

from code.render.glfunctions import *

from code.game.newsfeeder import Newsfeeder
from code.game.hud import HUD

from code.constants.common import FADE_CONCENTRIC, FADE_LTR
from code.constants.paths import FONT_PATH # The only one we need here 

from code.utils.common import log, log2, logn


# Local constants
DEFAULT_FONT_NAME = "jupiterc.ttf"
DEFAULT_FONT_SIZE = 18


# Sometimes I want a window controller without rendering capabilities, for batch scripts.  Kind of a bad hack.
class DebugWindowController:

    def __init__(self):

        # The window controller carries a newsfeeder to display status messages to the user throughout the game.
        self.newsfeeder = Newsfeeder()

    # Get the newsfeeder
    def get_newsfeeder(self):

        return self.newsfeeder


class WindowController(HookableExt):

    def __init__(self, render_width, render_height, screen_width, screen_height):

        HookableExt.__init__(self)


        # If we ever need to recreate the window (i.e. toggle fullscreen),
        # we'll set a flag here that the main app can monitor.
        self.reloaded = False


        # Reference the desired render region for the game
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Reference the actual render region (in case we needed a higher resolution (with extra space) for video card compatibility)
        self.render_width = render_width
        self.render_height = render_height


        # Active render target width.  This is the game window by default (e.g. 640x480),
        # but it changes whenever we shift to a scratch pad (to the scratch pad's dimensions).
        self.current_render_width = render_width
        self.current_render_height = render_height


        # Some languages require a separate font.
        # We'll default to a hard-coded value.
        self.font = DEFAULT_FONT_NAME

        # Default font size
        self.font_size = DEFAULT_FONT_SIZE


        # Alpha controller for entire game
        self.alpha_controller = IntervalController(
            interval = 1.0,
            target = 1.0,
            speed_in = 0.025,
            speed_out = 0.045
        )

        # Determine how to render the app-level fade
        self.fade_mode = FADE_LTR#CONCENTRIC # default

        # We might call for a delay on the fades from time to time
        self.delay_interval = 0


        # Create a scissor controller
        self.scissor_controller = ScissorController(render_width, render_height, screen_width, screen_height)

        # Create a stencil controller
        self.stencil_controller = StencilController()


        # Create a CSS controller
        self.css_controller = CSSController()


        # Create a geometry controller
        self.geometry_controller = GeometryController(
            render_offset_x = self.get_window_x(),
            render_offset_y = self.get_window_y()
        )

        # Create a graphics controller
        self.gfx_controller = GfxController(
            render_offset_x = self.get_window_x(),
            render_offset_y = self.get_window_y(),
            visibility_region = self.get_visibility_region()
        )

        # Create an empty hash to house text controllers.
        # We populate this hash when loading assets.
        self.text_controllers = {}

        # We can create scratch pads with given names.
        # Create the scratch pads in the loading assets function.
        self.scratch_pads = {}


        # We'll also have some shaders to choose from.
        # Create the shaders in the loading assets function.
        self.shaders = {}


        # The window controller can "cache" portions of the active framebuffer
        # for future use.  I commonly use this to cache larger blocks of text.
        # The text renderer will keep track of any cached items...
        self.cache_items = {}


        # We can assign parameters / attributes to the window controller.  We'll use this
        # sometimes to "save" values when we begin a fade, so that we can "remember" what to
        # do with them when the fade concludes.
        self.params = {}


        # The window controller carries a newsfeeder to display status messages to the user throughout the game.
        self.newsfeeder = Newsfeeder()


        # The window controller also carries a HUD object to display various information to the player (bombs, gold, etc.)
        self.hud = HUD()


    # Set reloaded status
    def set_reloaded(self, value):

        # Update setting
        self.reloaded = value


    # Check to see if we reloaded the window
    def has_reloaded(self):

        # Simple check
        return self.reloaded


    # Set active font
    def set_font(self, font):

        # Don't respond to duplicate overwrites
        if (self.font != font):

            # Update tracked font
            self.font = font


            # Clear active text controllers
            self.text_controllers.clear()

            # Reload fonts
            self.text_controllers = self.load_gl_fonts()


    # Set font to default
    def set_font_to_default(self):

        # Default font size
        self.set_font_size(DEFAULT_FONT_SIZE)

        # Update
        self.set_font(DEFAULT_FONT_NAME)


    # Get active font
    def get_font(self):

        # Return string
        return self.font


    # Set font size
    def set_font_size(self, size):

        # Set
        self.font_size = size


    # Get font size
    def get_font_size(self):

        # Return
        return self.font_size


    # Load (or reload) all font assets.
    # Returns a hash of text controller objects.
    def load_gl_fonts(self):

        return {

            "default": TextController(
                render_offset_x = self.get_window_x(),
                render_offset_y = self.get_window_y(),
                #text_renderer = GLTextRenderer(os.path.join(FONT_PATH, 'jupiterc.ttf'), (255, 255, 255), (0, 0, 0), 18)
                text_renderer = GLTextRenderer( os.path.join( FONT_PATH, self.get_font() ), (255, 255, 255), (0, 0, 0), self.get_font_size() )
            ),

            "high-contrast": TextController(
                render_offset_x = self.get_window_x(),
                render_offset_y = self.get_window_y(),
                text_renderer = GLTextRenderer( os.path.join( FONT_PATH, self.get_font() ), (0, 0, 0), (175, 175, 175), self.get_font_size() )
            ),

            "gui": TextController(
                render_offset_x = self.get_window_x(),
                render_offset_y = self.get_window_y(),
                text_renderer = GLTextRenderer( os.path.join( FONT_PATH, self.get_font() ), (255, 255, 255), (0, 0, 0), self.get_font_size() )
            )

        }


    # Load (or reload) all game image-related assets
    def load_gl_assets(self):

        # Load all image data
        self.gfx_controller.load_image_assets()


        # Create some text controllers
        self.text_controllers = self.load_gl_fonts()


        # Initialize scratch pads
        self.scratch_pads = {
            "parallax": ScratchPad(1024, 1024),     # Designed to carry parallax data only
            "common": ScratchPad(1024, 1024),       # General purpose scratch pad, used by anything
            "common2": ScratchPad(1024, 1024)       # Another such scratch pad
        }


        # Create shaders
        self.shaders = {
            "greyscale": create_greyscale_shader(),
            "directional-blur": create_directional_blur_shader()
        }


    # Unload all image-related assets
    def unload_gl_assets(self):

        # Clear all graphics
        self.gfx_controller.unload_image_assets()

        # Reset text controllers
        self.text_controllers.clear()


        # Delete all scratch pads.
        # Release each manually...
        for key in self.scratch_pads:

            # Unload resources
            self.scratch_pads[key].unload()

        # Clear hash
        self.scratch_pads.clear()


        # Delete all shader programs.
        # Currently must delete manually...
        for key in self.shaders:

            # Delete program
            delete_shader_program(self.shaders[key])

        # Clear hash
        self.shaders.clear()


    # Get a scratch pad by name
    def get_scratch_pad(self, name):

        # Validate
        if (name in self.scratch_pads):

            # Yep
            return self.scratch_pads[name]

        # 404
        else:
            return None


    # Render to primary frame buffer
    def render_to_primary(self):

        # Send 0s to C function
        render_to_scratch_pad(0, 0, 0)

        # Default back to primary surface dimensions
        self.current_render_width = self.render_width
        self.current_render_height = self.render_height


        # Resume the scissor testing, if it needs to be done...
        self.scissor_controller.resume()


    # Render to a given scratch pad
    def render_to_scratch_pad(self, name):

        # Fetch scratch pad
        scratch_pad = self.get_scratch_pad(name)

        # Validate
        if (scratch_pad):

            """
            log2(
                scratch_pad.get_buffer_id(),
                scratch_pad.get_width(),
                scratch_pad.get_height()
            )
            """

            # Pause scissor tests, I don't want them when using scratch pads, drives me crazy
            self.scissor_controller.force_pause()

            # Activate scratch pad
            render_to_scratch_pad(
                scratch_pad.get_buffer_id(),
                scratch_pad.get_width(),
                scratch_pad.get_height()
            )


            # Set current render dimensions to the scratch pad's dimensions
            self.current_render_width = scratch_pad.get_width()
            self.current_render_height = scratch_pad.get_height()


    # Activate a given shader
    def activate_shader(self, name):

        # Validate
        if (name in self.shaders):

            # Use the shader program
            use_program( self.shaders[name] )


    # End shader use
    def deactivate_shader(self):

        # Use program "0"
        use_program(0)


    # Configure the greyscale (shader) intensity (0 - 100)
    def configure_greyscale_intensity(self, percent):

        # Configure
        configure_greyscale_intensity( self.shaders["greyscale"], percent )


    # Configure the directional blur (shader)
    def configure_directional_blur(self, direction, length):

        # Configure
        configure_directional_blur( self.shaders["directional-blur"], direction, length )


    def xxxxx(self):
        self.buffer2 = create_framebuffer()
        self.texture2 = prepare_framebuffer_by_id(self.buffer2, 1024, 1024)
        self.shader1 = create_shader1()
        self.buffer5 = create_framebuffer()
        self.buffer5texture = prepare_framebuffer_by_id(self.buffer5, 1024, 1024)
    def select_framebuffer(self, param):
        log2("selecting framebuffer:  %s" % param)
        select_framebuffer(param)
    def set_viewport(self, x, y, w, h):
        set_viewport(x, y, w, h)
    def test_shader1(self, param):
        #select_framebuffer(self.buffer5)
        use_program(self.shader1, param)
        #select_framebuffer(0)
        #self.test_buffer2()
    def test_shader2(self):
        use_program(0, 0)
    def test_buffer2(self):
        select_framebuffer(self.buffer2)
        if (1):
            set_viewport(0, 0, 1024, 1024)
            #set_viewport(0, 0, 640, 480)
            if (1):
                for y in range(24, 1024, 72):
                    for x in range(24, 1024, 72):
                        (r, g, b) = (
                            50 + (25 * random.randint(0, 8)),
                            50 + (25 * random.randint(0, 8)),
                            50 + (25 * random.randint(0, 8))
                        )
                        self.get_geometry_controller().draw_rect(0 + (x), 0 + (y), 24, 24, (r, g, b))
                        self.get_default_text_controller().get_text_renderer().render_with_wrap( "(%d, %d)" % (x, y), x + 12, y + 24, (225, 225, 25), align = "center" )

            set_viewport(0, 0, 640, 480)
        select_framebuffer(0)
        log2("done")
    def drawbuffer2(self, sx, sy):
        #set_viewport(0, 0, 240, 240)
        draw_texture(self.buffer5texture, sx, sy, 1024, 1024)
        #set_viewport(0, 0, 640, 480)


    def get_scissor_controller(self):

        return self.scissor_controller


    def get_stencil_controller(self):

        return self.stencil_controller


    def get_css_controller(self):

        return self.css_controller


    def get_geometry_controller(self):

        return self.geometry_controller


    def get_gfx_controller(self):

        return self.gfx_controller


    def get_default_text_controller(self):

        return self.text_controllers["default"]


    def get_text_controller_by_name(self, name):

        # Validate
        if (name in self.text_controllers):

            return self.text_controllers[name]

        # Return default
        else:

            return self.text_controllers["default"]


    def get_window_x(self):

        return int(self.render_width / 2) - int(self.screen_width / 2)


    def get_window_y(self):

        return int(self.render_height / 2) - int(self.screen_height / 2)


    def get_visibility_region(self):

        return (
            self.get_window_x(),
            self.get_window_y(),
            self.screen_width,
            self.screen_height
        )


    def clip_backbuffer(self):

        return clip_backbuffer(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self)


    # Clear cached screen regions
    def clear_cache(self):

        # Clear the cache key dictionary.  This will cascade down to the
        # destructor for each item, releasing the textures...
        self.cache_items.clear()


    # Add a texture of a given size to the cache, by key
    def cache_texture_by_key(self, cache_key, texture_id, texture_size, about = ""):

        # If we already cached something by that key, we should delete it first...
        if ( self.cache_key_exists(cache_key) ):

            # This will trigger the deconstructor
            self.cache_items.pop(cache_key)


        # Now let's cache the new item
        self.cache_items[cache_key] = WindowCacheItem(texture_id, texture_size, about = about)


    # Check to see if a key exists in the screen region cache
    def cache_key_exists(self, cache_key):

        # Simple check
        return (cache_key in self.cache_items)


    # Render a cache item (by key) to a location on the screen
    def render_cache_item_by_key(self, cache_key, x, y, gl_color = (1, 1, 1, 1)):

        # Validate
        if ( self.cache_key_exists(cache_key) ):

            # Grab a handle to the item
            cache_item = self.cache_items[cache_key]

            # Render the texture we created as a "cache"
            self.get_gfx_controller().draw_texture(cache_item.get_texture_id(), x, y, cache_item.get_texture_size(), cache_item.get_texture_size(), color = gl_color)


    def pause_clipping(self):

        #pause_clipping()
        self.scissor_controller.pause()


    def resume_clipping(self):

        #resume_clipping()
        self.scissor_controller.resume()


    # Get the newsfeeder
    def get_newsfeeder(self):

        # Return
        return self.newsfeeder


    # Get the HUD
    def get_hud(self):

        # Return
        return self.hud


    # Delay processing on fades (and maybe other stuff, I guess)
    def delay(self, interval):

        # Track
        self.delay_interval = interval


    # Set the fade rendering style
    def set_fade_mode(self, mode):

        self.fade_mode = mode


    def fade_out(self, on_complete = ""):
        logn(3, "Fade out...", "--detailed")

        self.alpha_controller.dismiss(
            target = 0.0,
            on_complete = on_complete
        )


    def fade_in(self, on_complete = ""):
        logn(3, "Fade in...", "--detailed")

        self.alpha_controller.summon(
            target = 1.0,
            on_complete = on_complete
        )


    # Set a parameter
    def set_param(self, key, value):

        # If a parameter by that key exists, let's clear it...
        if (key in self.params):

            # Get rid of it
            self.params.pop(key)


        # Save the new param
        self.params[key] = value


    # Try to get a parameter
    def get_param(self, key):

        # Validate
        if (key in self.params):

            return self.params[key]

        # 404
        else:
            return None


    # Check to see if a parameter name exists
    def has_param(self, key):

        # Simple check for key
        return (key in self.params)


    # Remove a parameter
    def remove_param(self, key):

        # Validate
        if (key in self.params):

            # Clear param
            self.params.pop(key)


    def process(self, control_center, universe):

        # Events that result from processing
        results = EventQueue()


        # Keep track of local results
        local_results = EventQueue()

        # Delay?
        if (self.delay_interval > 0):

            # Wait a tick
            self.delay_interval -= 1

        # Green light
        else:

            # Process alpha
            local_results.append(
                self.alpha_controller.process()
            )


        # Always process the newsfeeder
        self.newsfeeder.process(control_center, universe)


        # Handle events
        event = local_results.fetch()

        # Every last one of them
        while (event):

            results.inject_event(event)

            logn( "window-event", (event.get_action(), event.get_params()) )

            # forward the event to any hooked-in listener
            results.append(
                self.forward_event_to_listeners(event, control_center, universe)
            )

            # Loop
            event = local_results.fetch()


        # Return events
        return results


    # Render an app-level fade effect based on a given alpha controller
    def render_fade_using_alpha_controller(self, mode, alpha_controller):

        # Kind of a spotlight effect
        if (mode == FADE_CONCENTRIC):

            # Center point
            (cx, cy) = (
                int(self.screen_width / 2),
                int(self.screen_height / 2)
            )

            # Determine radius
            radius = int( math.sqrt( (cx * cx) + (cy * cy) ) )

            # Render fade
            self.get_geometry_controller().draw_circle_with_radial_gradient(cy, cy, radius, background1 = (0, 0, 0, 1.0 - (self.alpha_controller.get_interval() - 0.25)), background2 = (0, 0, 0, (1.0 - self.alpha_controller.get_interval())))

        # Left-to-right fade
        elif (mode == FADE_LTR):

            # Fade in very smoothly
            if ( alpha_controller.get_target() > 0 ):

                # Based on the percentage of alpha visibility, decide how much of the screen we should reveal;
                # the rest will remain black until the fade reaches that far.  Then, multiply that cursor location
                # by 2 so that we can do a second pass, continuing the brightening effect.
                rx = int( ( alpha_controller.get_interval() / alpha_controller.get_target() ) * self.screen_width ) * 2

                # The first pass is straightforward
                if (rx <= self.screen_width):

                    # Simple gradient reveal of the visible region
                    self.get_geometry_controller().draw_rect_with_horizontal_gradient(0, 0, rx, self.screen_height, (0, 0, 0, 1.0 - alpha_controller.get_interval()), (0, 0, 0, 1))

                    # Black out the rest of the screen completely
                    self.get_geometry_controller().draw_rect(rx, 0, self.screen_width - rx, self.screen_height, (0, 0, 0))

                # At the end of the first pass, we're drawing a gradient across the entire screen.  We don't want to suddenly
                # lift the gradient entirely; it looks awful, very distracting.  Instead, we'll continue on a "second pass,"
                # shrinking the region on which we draw the "final gradient," in effect gradually setting more and more of the
                # screen to 100% bright / visible.
                else:

                    # As we leave the left edge of the screen behind, we will continue to mask it (but with no gradient) according to the current alpha fade value.
                    self.get_geometry_controller().draw_rect(0, 0, (rx - self.screen_width), self.screen_height, (0, 0, 0, 1.0 - alpha_controller.get_interval()))


                    # When we first begin the second pass, we will be drawing a very wide rectangle (from alpha ~0.5 to alpha ~1.0).
                    # Over time, the width of "still fading in" region gets smaller and smaller, making the resulting gradient change
                    # awkwardly.  To compensate for this, I will gradually lower the "end gradient" alpha setting, starting at 1.0
                    # and becoming lower and lower as the second pass progresses.  It's definitely a fudge job, but it looks pretty good.
                    fudge = 1.0 - ( (0.5 - ( 1.0 - alpha_controller.get_interval() )) / 0.5 )

                    # Render a gradient on the remaining untouched region
                    self.get_geometry_controller().draw_rect_with_horizontal_gradient(rx - self.screen_width, 0, self.screen_width - (rx - self.screen_width), self.screen_height, (0, 0, 0, 1.0 - alpha_controller.get_interval()), (0, 0, 0, fudge))

            # I don't care as much about abrupt lighting changes when fading out; it's less noticeable!
            else:

                rx = int( ( (0.0 + alpha_controller.get_interval()) / (1.0 - alpha_controller.get_target()) ) * self.screen_width )

                self.get_geometry_controller().draw_rect_with_horizontal_gradient(0, 0, rx, self.screen_height, (0, 0, 0, 1.0 - alpha_controller.get_interval()), (0, 0, 0, 1))

                self.get_geometry_controller().draw_rect(rx, 0, self.screen_width - rx, self.screen_height, (0, 0, 0))

