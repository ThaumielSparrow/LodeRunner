#from glfunctions import draw_rect, draw_rect_frame, draw_rect_with_horizontal_gradient, draw_rect_with_vertical_gradient, draw_rounded_rect, draw_clock_rect, draw_sprite, draw_circle_with_radial_gradient

from code.utils.common import log, log2

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_ELEMENT_LENGTH, HUD_ELEMENT_HEIGHT, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, DIR_LEFT, DIR_RIGHT, WALLET_TICK_DELAY_MAX, HUD_NOTE_LIFESPAN, HUD_NOTE_ALPHA_MAX, HUD_NOTE_FADE_IN_END, HUD_NOTE_FADE_OUT_BEGIN

from code.controllers.intervalcontroller import IntervalController

class HUD:

    def __init__(self):

        # Set up the various icons...
        self.skill_icons = {
            "sprint": HUDIcon("sprint", "Sprint", (0, 0), 60),
            "matrix": HUDIcon("matrix", "Matrix", (3, 3), -1),
            "hologram": HUDIcon("hologram", "Hologram", (4, 4), 60),
            "fright": HUDIcon("fright", "Fright", (7, 7), 60),
            "jackhammer": HUDIcon("jackhammer", "Jackhammer", (9, 9), 60),
            "earth-mover": HUDIcon("earth-mover", "Earth Mover", (12, 12), 60),
            "personal-shield": HUDIcon("personal-shield", "Personal Shield", (15, 15), -1),
            "wall": HUDIcon("wall", "Wall", (16, 16), -1),
            "remote-bomb": HUDIcon("remote-bomb", "Remote Bomb", (17, 17), -1),
            "mega-bomb": HUDIcon("mega-bomb", "Mega Bomb", (18, 18), -1),
            "invisibility": HUDIcon("invisibility", "Invisibility", (19, 19), 60),
            "pickpocket": HUDIcon("pickpocket", "Pickpocket", (22, 22), 60),
            "puzzle-room": HUDIcon("", "Pickpocket", (22, 22), 60),
        }


        # Bomb count and gold count (i.e. wallet)
        self.stat_icons = {
            "bombs": HUDIcon("bombs", "Bombs", (0, 0), -1),
            "wallet": HUDIcon("wallet", "Gold", (1, 1), -1)
        }

        # As the player acquires gold, the counter will tick upward to reach the actual
        # value.  This timer determines when we can tick the value forward, if necessar.
        self.wallet_tick_delay = 0


        # Occasionally, the HUD will cycle through a list of notes.  For example, when the player completes
        # a level, the HUD will show "level complete" and other bonus messages.
        self.notes = []

        # Each time we find a new note, we'll display it for some given length of time
        self.note_lifespan = HUD_NOTE_LIFESPAN


        # Alpha control
        self.alpha_controller = IntervalController(
            interval = 0.0,
            target = 1.0,
            speed_in = 0.015,
            speed_out = 0.035
        )


    def show(self):

        self.alpha_controller.summon()


    def hide(self):

        self.alpha_controller.dismiss()


    # Add one or more notes to the HUD
    def add_notes(self, notes):

        # Import
        self.notes.extend(notes)


    # Get a hash with information about how to render the XP bar and any HUD notes.
    def get_xp_bar_data(self, universe, session):

        xp_display_interval = int( universe.get_session_variable("core.xp-bar.timer").get_value() )

        # Anything worth showing?
        if (xp_display_interval > 0):

            (xp_percent_old, xp_percent_new, xp_display_interval, xp_display_interval_max) = (
                float( universe.get_session_variable("core.xp-bar.percent-old").get_value() ),
                float( universe.get_session_variable("core.xp-bar.percent-new").get_value() ),
                int( universe.get_session_variable("core.xp-bar.timer").get_value() ),
                int( universe.get_session_variable("core.xp-bar.timer-max").get_value() )
            )

            # Difference between old and new percentages
            dx = (xp_percent_new - xp_percent_old)

            # How much of the difference will we show?
            visible_percent = 0

            # Prevent division by zero
            if (xp_display_interval_max != 0):
                visible_percent = xp_percent_old + float( ( (xp_display_interval_max - xp_display_interval) / float(xp_display_interval_max)) * dx )

            label = universe.get_session_variable("core.xp-bar.total-earned").get_value()#"+100 XP"

            #if (xp_display_interval == xp_display_interval_max - 1):
            #    label = "XP Bonus"
            #    log( "LABEL:  ", label )


            # Usually render message at 100% alpha
            alpha_factor = 1.0

            # At the beginning and end x%, though, it will fade in/out
            timer_threshold = 30

            if ( xp_display_interval < timer_threshold ):

                alpha_factor = xp_display_interval / float(timer_threshold)

            elif ( (xp_display_interval_max - xp_display_interval) < timer_threshold ):

                alpha_factor = (xp_display_interval_max - xp_display_interval) / float(timer_threshold)

            log( "factor:  ", alpha_factor )


            return {
                "active": True,
                "percent": visible_percent,
                "message": label,
                "alpha-factor": alpha_factor
            }

            """
            return (
                (visible_percent),
                (219, 183, 21),
                label,
                (xp_display_interval <= 0)
            )
            """

        # Nope; we're inactive.  Let's just return the current progress towards next level up...
        else:

            # Use wherever we left off after last XP gain...
            xp_current_percent = float( universe.get_session_variable("core.xp-bar.percent-new").get_value() )

            return {
                "active": False,
                "percent": xp_current_percent
            }


    def process(self, universe, session):

        # Process alpha
        self.alpha_controller.process()


        # Process the active skill icons
        for i in range(1, 3):

            skill = universe.get_session_variable("core.player1.skill%d" % i).get_value()

            if (skill in self.skill_icons):

                self.skill_icons[skill].process()


    def render(self, x, y, text_renderer, universe, session, is_puzzle_room, is_challenge_room, skill_icons_sprite, hud_icons_sprite, window_controller):

        # Constants
        icon_padding = 5
        hud_element_padding = 24

        margin = 16


        # Darken area on which we'll render the HUD
        window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(0, 0, SCREEN_WIDTH, (icon_padding + SKILL_ICON_HEIGHT + int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)), (20, 20, 20, 1.0), (20, 20, 20, 0.5))

        # Underline just for a little separation
        window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(0, (icon_padding + SKILL_ICON_HEIGHT + int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)), SCREEN_WIDTH, 2, (85, 85, 85, 0.35), (155, 155, 155, 0.25))


        # Fetch the active map
        m = universe.get_active_map()


        # Determine what to do with the XP bar
        params = self.get_xp_bar_data(universe, session)

        # Actively progressing?  Render a potential message and an aura effect...
        if (params["active"] == True):

            # Render XP bar
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(0, (icon_padding + SKILL_ICON_HEIGHT + int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)), int(params["percent"] * SCREEN_WIDTH), 2, (207, 106, 19, 0.35), (207, 106, 19, 0.35))


            # Calculate aura render position
            (x, y) = (
                int(params["percent"] * SCREEN_WIDTH),
                (icon_padding + SKILL_ICON_HEIGHT + int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2))
            )

            """
            # Display label (e.g. "40 xp bonus!")
            if (params["message"] != ""):

                # Arranged as csv (well, semicolon...)
                pieces = params["message"].split(";")

                for i in range(0, len(pieces)):
                    window_controller.get_default_text_controller().render(pieces[i].strip(), 10, y + 5 + (i * window_controller.get_default_text_controller().get_text_renderer().font_height), p_color = (225, 225, 225, params["alpha-factor"] * 0.5), p_color2 = (225, 195, 175, params["alpha-factor"] * 0.5), p_align = "left")
            """

            # Calculate size of XP earned subtitle
            w = window_controller.get_default_text_controller().get_text_renderer().size( params["message"] )

            # As we move along the x-axis / progress bar, we will adjust the alignment from left-aligned (at the beginning) to right-aligned (by the end).
            window_controller.get_default_text_controller().render(
                params["message"],
                x - int( ( float(x) / SCREEN_WIDTH ) * w ),
                y - window_controller.get_default_text_controller().get_text_renderer().font_height - 5,
                p_color = (225, 225, 225, params["alpha-factor"] * 0.5),
                p_color2 = (225, 195, 175, params["alpha-factor"] * 0.5),
                p_align = "left" # "Left," although we're manually offsetting the x coordinate as we move along the progress bar
            )

            # Show an aura around the lead...
            window_controller.get_geometry_controller().draw_circle_with_radial_gradient(x, y, radius = 5, background1 = (225, 225, 225, params["alpha-factor"] * 0.3), background2 = (225, 225, 225, params["alpha-factor"] * 0.1))

        # No; render the current progress with no message / aura
        else:
            window_controller.get_geometry_controller().draw_rect_with_horizontal_gradient(0, (icon_padding + SKILL_ICON_HEIGHT + int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)), int(params["percent"] * SCREEN_WIDTH), 2, (207, 106, 19, 0.35), (207, 106, 19, 0.35))

            # Display label (e.g. "40 xp bonus!")
            #if (True or params["message"] != ""):
            #    window_controller.get_default_text_controller().render("Text test...", x, y, p_color = (155, 155, 155, 0.5), p_color2 = (225, 225, 225, 0.5), p_align = "right")


        # Check to see if we have an active note to render
        if ( len(self.notes) > 0 ):

            # Decrement lifespan of current note
            self.note_lifespan -= 1

            # Done?
            if (self.note_lifespan <= 0):

                # Reset timer for next possible note
                self.note_lifespan = HUD_NOTE_LIFESPAN

                # Remove expired note
                self.notes.pop(0)

            # Not done; let's render it...
            else:

                # As a percentage, how far into the lifespan are we?
                percent = 1.0 - (self.note_lifespan / float(HUD_NOTE_LIFESPAN))

                # Assume
                alpha = HUD_NOTE_ALPHA_MAX

                # If it's just started, let's fade it in
                if (percent <= HUD_NOTE_FADE_IN_END):

                    # Compute proper alpha value
                    alpha = (percent / HUD_NOTE_FADE_IN_END) * HUD_NOTE_ALPHA_MAX

                # If it's almost done, let's fade it out
                elif (percent >= HUD_NOTE_FADE_OUT_BEGIN):

                    # Compute proper alpha value
                    alpha = ( 1.0 - ( (percent - HUD_NOTE_FADE_OUT_BEGIN) / (1.0 - HUD_NOTE_FADE_OUT_BEGIN) ) ) * HUD_NOTE_ALPHA_MAX


                # Render note
                window_controller.get_default_text_controller().render(
                    self.notes[0],
                    10,
                    (icon_padding + SKILL_ICON_HEIGHT + int(window_controller.get_default_text_controller().get_text_renderer().font_height / 1)),
                    p_color = (225, 225, 225, alpha),
                    p_color2 = (225, 195, 175, alpha)
                )
                #pieces[i].strip(), 10, y + 5 + (i * window_controller.get_default_text_controller().get_text_renderer().font_height), p_color = (225, 225, 225, params["alpha-factor"] * 0.5), p_color2 = (225, 195, 175, params["alpha-factor"] * 0.5), p_align = "left")

        # Establish initial rendering position
        (rx, ry) = (
            SCREEN_WIDTH - margin,
            icon_padding#SCREEN_HEIGHT - SKILL_ICON_HEIGHT - icon_padding
        )


        if (is_puzzle_room):

            # Generic label
            icon_label = "Puzzle Room"

            # Calculate the width of the title
            text_width = window_controller.get_default_text_controller().get_text_renderer().size(icon_label)

            # Padding
            text_padding = 10

            # Calculate render width
            render_width = (SKILL_ICON_WIDTH + text_padding + text_width)

            # Align to the right
            rx -= render_width

            # Render puzzle icon at the edge of the screen
            window_controller.get_gfx_controller().draw_sprite(rx - SKILL_ICON_WIDTH, ry, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, hud_icons_sprite, frame = 2, gl_color = (1, 1, 1, max(0, self.alpha_controller.get_interval() - 0.35)))

            # Subscript
            if (True):
                ry += int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)

            rx += text_padding

            window_controller.get_default_text_controller().render(icon_label, rx, ry, (225, 225, 225, self.alpha_controller.get_interval()))

        # Hey, let's render standard HUD for challenge rooms huh?
        elif (False and is_challenge_room):

            pass

        else:

            for slot in (2, 1):

                # Render the skill, if it has any assigned...
                skill = universe.get_session_variable("core.player1.skill%d" % slot).get_value()

                if (skill in self.skill_icons):

                    # Calculate radial fill angle / color
                    clock_angle = 0
                    clock_color = (239, 225, 143, 0.5)

                    # Dim the icon if it's recharging...
                    alpha_penalty = 0

                    # Is the skill needing to recharge?
                    recharge_remaining = int( universe.get_session_variable("core.skills.%s:recharge-remaining" % skill).get_value() )

                    if (recharge_remaining >= 0):

                        # Do we have any time left on the duration of this skill?
                        time_remaining = int( universe.get_session_variable("core.skills.%s:timer" % skill).get_value() )

                        # If the timer on the skill is still executing, then display a gold clock radial that counts "down"...
                        if (time_remaining > 0):

                            # Gold clock
                            clock_color = (219, 183, 21, 1.0)

                            # Divisor
                            time_potential = float( universe.get_session_variable("core.skills.%s:timer-max" % skill).get_value() )

                            log( skill )

                            # Calculate clock angle
                            clock_angle = int( (time_remaining / time_potential) * 360 )

                        # Otherwise, display the "recharge progress" as the skill nears availability, using an off-white color...
                        elif (recharge_remaining > 0):

                            # White clock
                            clock_color = (155, 21, 21, 1.0)

                            # Divisor
                            recharge_potential = float( universe.get_session_variable("core.skills.%s:recharge-potential" % skill).get_value() )

                            # Calculate clock angle
                            clock_angle = 360 - (int( (recharge_remaining / recharge_potential) * 360 ))

                            # Because the skill is recharging, we shall dim the icon...
                            alpha_penalty = 0.35


                    # Define a cache key
                    cache_key = "skill-label-%d" % slot

                    # Track whether or not that key may have expired...
                    cache_expired = (universe.get_session_variable("core.player1.skill%d:changed" % slot).get_value() == "1")


                    # Render and offset cursor
                    rx -= self.skill_icons[skill].render(cache_key, cache_expired, rx, ry, skill_icons_sprite, text_renderer, text_align = DIR_RIGHT, session = session, window_controller = window_controller, alpha = self.alpha_controller.get_interval() - alpha_penalty, align = DIR_RIGHT, subscript = True, clock_angle = clock_angle, clock_color = clock_color)
                    rx -= hud_element_padding


                    # If the cache key had previous expired, we've now updated it accordingly...
                    universe.set_session_variable("core.player1.skill%d:changed" % slot, "0")




        # Render bomb count and wallet amount
        (rx, ry) = (
            icon_padding + margin,
            icon_padding#SCREEN_HEIGHT - SKILL_ICON_HEIGHT - icon_padding
        )


        # Set bomb count text.  In a puzzle room, we'll use the difference between the "wave" bomb allowance
        # and the number of bombs the player has used in the puzzle room.
        if ( m.get_param("type") in ("puzzle", "challenge") ):

            # Calculate bombs remaining
            (a, b) = (
                m.get_wave_tracker().get_wave_counter("bombs"),
                m.get_wave_tracker().get_wave_allowance("bombs")
            )

            # -1 indicates an infinite allowance of bombs...
            if (b == -1):

                # Special case
                self.stat_icons["bombs"].title = "Inf."

            else:

                # Make sure we don't display a negative number
                self.stat_icons["bombs"].title = "%s" % max( 0, (b - a) )

        # Otherwise, in the overworld / co-op / whatever, use the core bomb counter
        else:

            # Set label
            self.stat_icons["bombs"].title = "%s" % universe.get_session_variable("core.bombs.count").get_value()


        # Render bombs, adjust cursor...
        rx += self.stat_icons["bombs"].render(None, False, rx, ry, hud_icons_sprite, text_renderer, text_align = DIR_RIGHT, session = session, window_controller = window_controller, alpha = self.alpha_controller.get_interval(), align = DIR_LEFT, subscript = True)
        rx += hud_element_padding


        # Get wallet data
        (wallet_actual, wallet_visible) = (
            int( universe.get_session_variable("core.gold.wallet").get_value() ),
            int( universe.get_session_variable("core.gold.wallet:visible").get_value() )
        )

        # If the visible counter is lagging behind the real value, let's consider incrementing it
        if (wallet_visible != wallet_actual):

            # Lessen the HUD's tick delay
            self.wallet_tick_delay -= 1

            # Ready to increment?
            if (self.wallet_tick_delay <= 0):

                # Reset for next tick
                self.wallet_tick_delay = WALLET_TICK_DELAY_MAX

                # Tick faster if the value becomes too disparate...
                for i in range( 0, int( abs(wallet_actual - wallet_visible) / 20 ) ):

                    # 25% faster for each multiple
                    self.wallet_tick_delay = int( 0.75 * self.wallet_tick_delay )


                # Received a lot of gold?
                if (wallet_visible < wallet_actual):

                    # Increment visible value.  The player won't actually "see" this change until the next frame, which seems fine to me.
                    universe.get_session_variable("core.gold.wallet:visible").increment_value(1)

                # Spent a lot of gold?
                else:

                    # Decrement visible value
                    universe.get_session_variable("core.gold.wallet:visible").increment_value(-1)


        # In puzzle / linear levels, we render the amount of gold collected / possible on the current level.
        if ( m.get_param("type") in ("puzzle", "linear") ):

            # Set text to "collected" / "possible"
            self.stat_icons["wallet"].title = "%s / %s" % ( m.collected_gold_count(), m.get_gold_count() )

            # Render wallet icon, text
            self.stat_icons["wallet"].render(None, False, rx, ry, hud_icons_sprite, text_renderer, text_align = DIR_RIGHT, session = session, window_controller = window_controller, alpha = self.alpha_controller.get_interval(), align = DIR_LEFT, subscript = True)

        # On overworld maps, we render the player's wallet total
        elif ( m.get_param("type") == "overworld" ):

            # Set wallet text
            self.stat_icons["wallet"].title = "%s gold" % wallet_visible

            # Render wallet icon, text
            self.stat_icons["wallet"].render(None, False, rx, ry, hud_icons_sprite, text_renderer, text_align = DIR_RIGHT, session = session, window_controller = window_controller, alpha = self.alpha_controller.get_interval(), align = DIR_LEFT, subscript = True)

        # Note that we don't display a gold quantity for any other map type (e.g. no gold icon in challenge rooms)


class HUDIcon:

    def __init__(self, name, title, frame_bounds, loop_delay):

        # name (e.g. "remote-bomb")
        self.name = name

        # formal title (e.g. "Remote Bomb")
        self.title = title


        # The range of "tiles" in the skill icons spritesheet relevant to this icon
        self.frame_bounds = frame_bounds

        # The currently displayed frame
        self.frame = self.frame_bounds[0]

        # Animation delay
        self.animation_delay = 0
        self.animation_delay_max = 10


        # For how long to delay before recycling the animation
        self.loop_delay = loop_delay
        self.loop_delay_max = loop_delay

    def process(self):

        (a, b) = self.frame_bounds

        # Maybe loopback delay...
        if (self.loop_delay > 0):

            self.loop_delay -= 1

        # Animate?
        else:

            # No reason to "animate" single-frame icons
            if (b > a):

                self.animation_delay += 1

                if (self.animation_delay >= self.animation_delay_max):

                    self.animation_delay = 0

                    self.frame += 1

                    if (self.frame > b):

                        # back to first frame
                        self.frame = a

                        # loop delay...
                        self.loop_delay = self.loop_delay_max

    def render(self, cache_key, cache_expired, x, y, sprite, text_renderer, text_align, session, window_controller, alpha, align, subscript = False, clock_angle = 0, clock_color = (225, 225, 225, 0.45)):

        # Calculate the width of the title
        text_width = window_controller.get_default_text_controller().get_text_renderer().size(self.title)

        # Padding
        text_padding = 10


        # Calculate render width
        render_width = (SKILL_ICON_WIDTH + text_padding + text_width)


        if (align == DIR_RIGHT):

            x -= render_width


        # Defaults
        (rx, ry) = (0, 0)


        if (text_align == DIR_LEFT):

            (rx, ry) = (x - text_width - text_padding - SKILL_ICON_WIDTH, y)

            #draw_rect(x - SKILL_ICON_WIDTH, y, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, (225, 0, 0))
            if (clock_angle):

                window_controller.get_geometry_controller().draw_clock_rect(rx - SKILL_ICON_WIDTH, ry, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, background = clock_color, degrees = clock_angle)

            # Render icon at the edge of the screen
            window_controller.get_gfx_controller().draw_sprite(rx - SKILL_ICON_WIDTH, ry, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, sprite, frame = self.frame, gl_color = (1, 1, 1, max(0, alpha - 0.35)))

            if (subscript):
                ry += int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)

            rx += text_padding

            #window_controller.get_default_text_controller().render(self.title, rx, ry, (225, 225, 225, alpha))

        elif (text_align == DIR_RIGHT):

            (rx, ry) = (x, y)

            if (clock_angle):
                window_controller.get_geometry_controller().draw_clock_rect(rx, ry, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, background = clock_color, degrees = clock_angle)

            # Render icon at the edge of the screen
            window_controller.get_gfx_controller().draw_sprite(rx, ry, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, sprite, frame = self.frame, gl_color = (1, 1, 1, alpha))

            if (subscript):
                ry += int(window_controller.get_default_text_controller().get_text_renderer().font_height / 2)

            rx += (SKILL_ICON_WIDTH + text_padding)

            #window_controller.get_default_text_controller().render_with_wrap(self.title, rx, ry, (225, 225, 225, alpha))


        if (self.title != ""):

            # Do we want to try to cache this item?
            if (cache_key):

                # If the window controller hasn't cached this label yet, then we'll want to cache it first...
                if ( (not window_controller.cache_key_exists(cache_key)) or (cache_expired) ):

                    # Let's flip over to the common scratch pad for a moment
                    window_controller.render_to_scratch_pad("common")

                    # Render the text with wrap (to the common scratch pad).  Retrieve the portion of the screen we used to render the text.
                    (texture_id, s, s) = text_renderer.render_and_clip_with_wrap(self.title, color = (219, 183, 21, 1), color2 = (155, 155, 155), window_controller = window_controller) # hard-coded colors!

                    # Feed the "cached" screen area to the window controller's cache.
                    window_controller.cache_texture_by_key(cache_key, texture_id, s, about = self.title)

                    # Make sure we resume rendering ot the primary framebuffer
                    window_controller.render_to_primary()


                # Now that we have ensured that the label is cached, we can render from cache
                window_controller.render_cache_item_by_key(cache_key, rx, ry)


            # If we don't want to cache it ever, then we'll just render it normally
            else:

                text_renderer.render_with_wrap(self.title, rx, ry, color = (219, 183, 21, 1), color2 = (155, 155, 155)) # hard-coded colors!
            # Render text label
            #cache_item = window_controller.get_default_text_controller().get_cache_item(cache_key)
            #if (cache_item and (not cache_expired)):
            #    cache_item.render(rx, ry, window_controller = window_controller)
            #else:
            #    window_controller.get_default_text_controller().render_with_wrap(self.title, rx, ry, (219, 183, 21, 1.0), color2 = (155, 155, 155), cache_key = cache_key)


        # Return the width we used to render this HUD element
        return render_width

    def render_with_recharge_progress(self, x, y, sprite, text_renderer, text_align, session, window_controller):

        window_controller.get_gfx_controller().draw_sprite(x, y, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, sprite, frame = self.frame)

        text_padding = 10

        if (text_align == DIR_LEFT):

            (recharge_remaining, recharge_potential) = (
                int( universe.get_session_variable("core.skills.%s:recharge-remaining" % self.name).get_value() ),
                int( universe.get_session_variable("core.skills.%s:recharge-potential" % self.name).get_value() )
            )

            (rx, ry) = (x - window_controller.get_default_text_controller().get_text_renderer().size(self.title) - text_padding, y)

            # Grey out the label if recharge remains...
            if (recharge_remaining > 0):

                # Also grey out the icon...
                window_controller.get_geometry_controller().draw_rect(x, y, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, (0, 0, 0, 0.75))

                window_controller.get_default_text_controller().render(self.title, rx, ry, (125, 125, 125))

                # Render default white font in accordance with the percentage of recharge attained...
                percent = (recharge_potential - recharge_remaining) / float(recharge_potential)

                w = int( percent * window_controller.get_default_text_controller().get_text_renderer().size(self.title) )

                # Scissor on that region...
                window_controller.get_scissor_controller().push( (rx, ry, w, window_controller.get_default_text_controller().get_text_renderer().font_height) )

                # Render brighter font
                window_controller.get_default_text_controller().render(self.title, rx, ry, (225, 225, 225))

                # End this scissor test
                window_controller.get_scissor_controller().pop()

            # Otherwise, normal font...
            else:

                window_controller.get_default_text_controller().render(self.title, rx, ry, (225, 225, 225))

        elif (text_align == DIR_RIGHT):

            (recharge_remaining, recharge_potential) = (
                int( universe.get_session_variable("core.skills.%s:recharge-remaining" % self.name).get_value() ),
                int( universe.get_session_variable("core.skills.%s:recharge-potential" % self.name).get_value() )
            )

            (rx, ry) = (x + SKILL_ICON_WIDTH + text_padding, y)

            # Grey out the label if recharge remains...
            if (recharge_remaining > 0):

                # Also grey out the icon...
                window_controller.get_geometry_controller().draw_rect(x, y, SKILL_ICON_WIDTH, SKILL_ICON_HEIGHT, (0, 0, 0, 0.75))

                window_controller.get_default_text_controller().render(self.title, rx, ry, (125, 125, 125))

                # Render default white font in accordance with the percentage of recharge attained...
                percent = (recharge_potential - recharge_remaining) / float(recharge_potential)

                w = int( percent * window_controller.get_default_text_controller().get_text_renderer().size(self.title) )

                # Scissor on that region...
                window_controller.get_scissor_controller().push( (rx + window_controller.get_default_text_controller().get_text_renderer().size(self.title) - w, ry, w, window_controller.get_default_text_controller().get_text_renderer().font_height) )

                # Render brighter font
                window_controller.get_default_text_controller().render(self.title, rx, ry, (225, 225, 225))

                # End that scissor test
                window_controller.get_scissor_controller().pop()


            # No more recharge needed...
            else:

                window_controller.get_default_text_controller().render(self.title, rx, ry, (225, 225, 225))
