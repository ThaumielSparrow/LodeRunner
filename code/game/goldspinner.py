import math

from particle import Particle

#from glfunctions import draw_sprite

from code.constants.common import GOLD_SPINNER_LIFESPAN, TILE_WIDTH, TILE_HEIGHT

from code.controllers.intervalcontroller import IntervalController

class GoldSpinner(Particle):

    def __init__(self, x, y, dest_x, dest_y):

        Particle.__init__(self, x, y, 0, 0, 0) # I don't care about tile index / particle index stuff


        # No alpha delay
        self.alpha_wait = 0


        # These things don't have gravity...
        self.gravity = 0
        self.max_gravity = 0


        # Calculate the distance between spawn and target
        distance = math.sqrt( ((x - dest_x) * (x - dest_x)) + ((y - dest_y) * (y - dest_y)) )

        # Calculate the angle between the spawn location and the target location...
        radians = (math.pi / 4)

        # Prevent division by 0
        if (dest_x != x):
            radians = math.atan( float(abs(dest_y - y)) / float(abs(dest_x - x)) )

        # The gold spinner has a given lifspan.  We must cross the distance in that duration...
        speed = float(distance) / float(GOLD_SPINNER_LIFESPAN)

        # Define rate of movement
        self.dx = int( math.cos(radians) * speed )
        self.dy = int( math.sin(radians) * speed )

        # Adjust +/- for the direction this gold is headed...
        if (x > dest_x):
            self.dx *= -1

        if (y > dest_y):
            self.dy *= -1

        # Based on destination coordinates and the time this particle is allowed to exist,
        # calculate an appropriate alpha fade speed...
        self.alpha_controller.set_speed_out( (1 / float(GOLD_SPINNER_LIFESPAN)) )


        # Define a rotational speed
        self.rotational_speed = -10


    def render(self, sx, sy, gold_sprite, window_controller):

        window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), TILE_WIDTH, TILE_HEIGHT, gold_sprite, frame = 0, gl_color = (1, 1, 1, self.alpha_controller.get_interval()), degrees = self.degrees)

