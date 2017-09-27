from code.tools.eventqueue import EventQueue

from code.extensions.common import HookableExt

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser

from code.utils.common import log, log2, get_flag_value

from code.constants.common import SPLASH_MODE_NORMAL, SPLASH_MODE_GREYSCALE_INSTANT, SPLASH_MODE_GREYSCALE_ANIMATED

class SplashController(HookableExt):

    def __init__(self):

        HookableExt.__init__(self)


        # Splash must track the original splash texture data at all times
        self.source_texture_id = None

        # Splash will also have a "working" version where we can apply greyscale on-the-fly and such
        self.working_texture_id = None


        # Invalidate the splash controller to ensure we get freshly drawn map data when we need it
        self.invalidated = True

        # We can "lock" the splash controller, forcing it to retain old contents / ignore fade in / fade out effects
        self.lock_count = 0


        # We'll want to track texture width / height whenever we initiate the splash
        self.width = 0
        self.height = 0


        # Current splash mode (animated, instant, whatever)
        self.mode = SPLASH_MODE_NORMAL


        # Splash can have a greyscale strength, which may animate in / out
        self.greyscale_controller = IntervalController(
            interval = 0,
            target = 0.75,
            speed_in = 0.05,
            speed_out = 0.05
        )


    def get_event_queue(self):

        return self.event_queue


    def invalidate(self):

        self.invalidated = True


    # Get the greyscale controller
    def get_greyscale_controller(self):

        # Return
        return self.greyscale_controller


    # Change the mode
    def set_mode(self, mode):

        # Set
        self.mode = mode

        # Invalidate contents
        self.invalidate()


    def is_dirty(self):

        return self.invalidated


    def lock(self):

        self.lock_count += 1


    def unlock(self):

        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            self.lock_count = 0


    def is_locked(self):

        return (self.lock_count > 0)


    def prepare(self, window_controller):

        # Make sure we're not locked
        if ( not self.is_locked() ):

            # If we previously saved a splash screen, let's release that texture before creating a new one...
            if (self.source_texture_id != None):

                # Free the texture
                window_controller.get_gfx_controller().delete_texture(self.source_texture_id)


            if (self.working_texture_id != None):

                # Free the texture
                window_controller.get_gfx_controller().delete_texture(self.working_texture_id)


            # Save splash data to a texture...
            (self.source_texture_id, self.width, self.height) = window_controller.clip_backbuffer()


            # Fetch the scratch pads we'll be using
            (common_scratch_pad, common2_scratch_pad) = (
                window_controller.get_scratch_pad("common"),
                window_controller.get_scratch_pad("common2")
            )


            # Render to the common scratch pad first
            window_controller.render_to_scratch_pad("common2")

            # Clear the common scratch pad
            window_controller.get_geometry_controller().draw_rect(0, 0, common_scratch_pad.get_width(), common_scratch_pad.get_height(), (20, 20, 20))


            # Intensity of blur (1.0 default. < 1.0 is a stronger blur, > 1.0 is a weaker blur)
            intensity = get_flag_value("menu_blur_intensity", XMLParser())#1.0#0.75

            # Try to cast as a float.  Invalid values (or empty string)
            # should raise an exception and default to 1.0.
            try:
                intensity = float(intensity)
            except:
                intensity = 1.0


            # Test blur effect
            # Horizontal blur pass to common scratch pad
            window_controller.render_to_scratch_pad("common")

            # Activate and configure directional blur shader
            window_controller.activate_shader("directional-blur")
            window_controller.configure_directional_blur(0, intensity * 1024.0)

            # Render to common with blur
            window_controller.get_gfx_controller().draw_texture( self.source_texture_id, 0, 0, self.width, self.height )


            # Render back to common2 scratch pad with the second directional blur pass (vertical)
            window_controller.render_to_scratch_pad("common2")

            # Configure already-active directional blur shader
            window_controller.configure_directional_blur(1, intensity * 1024.0)

            # Render with blur from the common pad (which holds the 1st pass)
            window_controller.get_gfx_controller().draw_texture( common_scratch_pad.get_texture_id(), 0, 0, common_scratch_pad.get_width(), common_scratch_pad.get_height() )

            # Deactivate shader
            window_controller.deactivate_shader()


            # Carry on rendering to primary framebuffer; we've completed the prerender, finally...
            window_controller.render_to_primary()


            # Copy from "parallax" scratch pad to the working texture id
            self.working_texture_id = window_controller.get_gfx_controller().clone_texture( common2_scratch_pad.get_texture_id(), 1024, 1024 )#window_controller.clip_backbuffer()



            # Now we have fresh data
            self.invalidated = False


            if ( self.mode == SPLASH_MODE_NORMAL ):

                self.greyscale_interval = 0
                self.greyscale_interval_target = 0

            elif ( self.mode == SPLASH_MODE_GREYSCALE_INSTANT ):

                self.greyscale_controller.set_interval(1.0)#0.75)
                self.greyscale_controller.set_target(1.0)#0.75)

                # Apply the greyscale effect right away to the working surface
                window_controller.get_gfx_controller().apply_greyscale_effect_to_texture( self.working_texture_id, self.width, self.height, self.greyscale_controller.get_target() )

            elif ( self.mode == SPLASH_MODE_GREYSCALE_ANIMATED ):

                #self.greyscale_controller.set_interval(0.0)
                self.greyscale_controller.set_target(1.0)#0.75)

                # Apply the greyscale effect right away to the working surface
                window_controller.get_gfx_controller().apply_greyscale_effect_to_texture( self.working_texture_id, self.width, self.height, self.greyscale_controller.get_target() )


    def dismiss(self, on_complete = ""):

        # Let's get out of here
        self.greyscale_controller.dismiss(
            on_complete = on_complete
        )


    # Instantly dismiss the entire splash, faded out entirely, etc.
    def abort(self, f_on_abort = None):

        # Bye byw
        self.greyscale_interval = 0
        self.greyscale_interval_target = 0

        # Callback?
        if (f_on_abort):

            f_on_abort()


    def is_lingering(self):

        return ( self.greyscale_controller.get_interval() > self.greyscale_controller.get_target() )


    def handle_event(self, event, control_center, universe):

        # Events resulting from handling this event
        results = EventQueue()

        # Convenience
        action = event.get_action()


        log2( "Splash controller event:  '%s'" % action )


        # Lock?
        if (action == "lock"):

            results.append(
                self.handle_lock_event(event, control_center, universe)
            )

        # Unlock?
        elif (action == "unlock"):

            results.append(
                self.handle_unlock_event(event, control_center, universe)
            )

        # Unpause game?
        elif (action == "game:unpause"):

            results.append(
                self.handle_game_unpause_event(event, control_center, universe)
            )

        else:
            log( "Unknown splash controller event '%s'" % action )


        # Return events
        return results


    # Lock the controller
    def handle_lock_event(self, event, control_center, universe):

        # Events resulting from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_action()


        # Simple
        self.lock()

        # Return events
        return results


    # Unlock the controller
    def handle_unlock_event(self, event, control_center, universe):

        # Events resulting from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_action()


        # So easy
        self.unlock()


        # Return events
        return results


    # Unpause the game
    def handle_game_unpause_event(self, event, control_center, universe):

        # Events resulting from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_action()


        # Unpause the game
        universe.unpause(force = True)

        # Disengage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })


        # Reset background music ratio to 100%
        control_center.get_sound_controller().set_background_ratio(1.0)


        # Return events
        return results


    def process(self, control_center, universe):

        # Events that result from processing the splash
        results = EventQueue()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Track current greyscale interval
        previous_interval  = self.greyscale_controller.get_interval()

        results.append(
            self.greyscale_controller.process()
        )

        # Grab now-current interval
        current_interval = self.greyscale_controller.get_interval()


        # Handle events
        event = results.fetch()

        # Loop all
        while (event):

            # Handle the event
            self.handle_event(event, control_center, universe)

            # Forward to any listener
            results.append(
                self.forward_event_to_listeners(event, control_center, universe)
            )


            # Loop
            event = results.fetch()

        # Return events
        return results


    def draw(self, window_controller):

        # Don't render if we don't have fresh data
        if ( not self.is_dirty() ):

            # Convenience
            interval = self.greyscale_controller.get_interval()

            #window_controller.get_gfx_controller().draw_texture(self.source_texture_id, 0, 0, self.width, self.height, color = (1, 1, 1, (1.0)))

            # Cross-fade
            window_controller.get_gfx_controller().draw_texture(self.source_texture_id, 0, 0, self.width, self.height, color = (1, 1, 1, (1.0 - interval)))
            window_controller.get_gfx_controller().draw_texture(self.working_texture_id, 0, 0, self.width, self.height, color = (1, 1, 1, interval))
