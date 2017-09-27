import random

from code.controllers.intervalcontroller import IntervalController

from code.constants.common import PARTICLE_WIDTH, PARTICLE_HEIGHT, COLORCLE_WIDTH, COLORCLE_HEIGHT, PARTICLE_SPAWN_GRAVITY, PARTICLE_SPAWN_GRAVITY_VARIANCE, PARTICLE_ROTATIONAL_SPEED, PARTICLE_ROTATIONAL_SPEED_VARIANCE, PARTICLE_RATE_OF_GRAVITY, PARTICLE_MAX_GRAVITY, NUMBERCLE_WIDTH, NUMBERCLE_HEIGHT, NUMBERCLE_LIFESPAN

#from glfunctions import draw_particle, draw_rect, draw_sprite

class Particle:

    def __init__(self, x, y, tile, index_x, index_y):

        self.state = True

        # Optional delay
        self.delay = 0

        self.x = x + (index_x * PARTICLE_WIDTH)
        self.y = y + (index_y * PARTICLE_HEIGHT)

        self.tile = tile

        self.index_x = index_x
        self.index_y = index_y

        self.gravity = PARTICLE_SPAWN_GRAVITY + (random.random() * random.randint(-PARTICLE_SPAWN_GRAVITY_VARIANCE, PARTICLE_SPAWN_GRAVITY_VARIANCE))
        self.max_gravity = PARTICLE_MAX_GRAVITY

        self.degrees = 0

        # I really don't want dx == 0 particles...
        self.dx = 0 + (random.random() * 3)

        if (random.randint(0, 10) <= 5):
            self.dx *= -1

        # Some particles may employ y movement
        self.dy = 0


        self.rotational_speed = PARTICLE_ROTATIONAL_SPEED + (random.random() * random.randint(0, PARTICLE_ROTATIONAL_SPEED_VARIANCE))

        if (self.dx < 0):
            self.rotational_speed *= -1


        # Alpha tracking
        self.alpha_wait = 30

        self.alpha_controller = IntervalController(
            interval = 1.0,
            target = 0.0,
            speed_in = 0.045,
            speed_out = 0.015
        )

    def get_x(self):
        return int(self.x)

    def get_y(self):
        return int(self.y)


    # Set a delay
    def set_delay(self, amount):

        # Set
        self.delay = amount


    def process(self, p_map):

        # Enforce delay?
        if (self.delay > 0):

            # Wait...
            self.delay -= 1

        # Ready!
        else:

            # I want to let the particles exist at full opacity for a moment before fading...
            if (self.alpha_wait > 0):

                self.alpha_wait -= 1

            # Process alpha
            else:

                self.alpha_controller.process()


            # Movement
            self.x += self.dx
            self.y += (self.dy + self.gravity)

            # Accelerate gravity
            self.gravity += PARTICLE_RATE_OF_GRAVITY

            if (self.gravity > self.max_gravity):
                self.gravity = self.max_gravity


            self.degrees += self.rotational_speed

            if (self.degrees < 0):
                self.degrees += 360

            elif (self.degrees >= 360):
                self.degrees -= 360


            if ( (self.y >= 1000) or ( not self.alpha_controller.is_visible() ) ):
                self.state = False

    def render(self, sx, sy, tilesheet_sprite, window_controller):

        window_controller.get_gfx_controller().draw_particle(sx + self.get_x(), sy + self.get_y(), self.index_x, self.index_y, self.degrees, self.tile, tilesheet_sprite, (255, 255, 255, self.alpha_controller.get_interval()))

class Colorcle(Particle):

    def __init__(self, x, y, color, color_range):

        Particle.__init__(self, x, y, -1, -1, -1) # I don't need the tile/index params

        # Base color
        self.color = color

        # Flickering colorcles
        self.color_range = color_range

    def render(self, sx, sy, window_controller):

        color = (
            self.color[0] + random.randint(-self.color_range[0], self.color_range[1]),
            self.color[1] + random.randint(-self.color_range[1], self.color_range[2]),
            self.color[2] + random.randint(-self.color_range[1], self.color_range[2]),
            self.color[3]
        )

        window_controller.get_geometry_controller().draw_rect(sx + self.get_x(), sy + self.get_y(), COLORCLE_WIDTH, COLORCLE_HEIGHT, color)

class Numbercle(Particle):

    def __init__(self, x, y, number):

        Particle.__init__(self, x, y, -1, -1, -1) # I'm going to ignore the tile/index params here, too...

        # Number
        self.number = number

        # lifespan
        self.lifespan = NUMBERCLE_LIFESPAN


        # Numbercles will have a dy just like particles have a dx; they won't have any gravity...
        self.dy = 0 + (random.random() * 3)

        if (random.randint(0, 10) <= 5):
            self.dy *= -1

    def process(self, p_map):

        self.x += self.dx
        self.y += self.dy


        self.degrees += self.rotational_speed

        if (self.degrees < 0):
            self.degrees += 360

        elif (self.degrees >= 360):
            self.degrees -= 360


        self.lifespan -= 1

        if (self.lifespan <= 0):
            self.state = False

    def render(self, sx, sy, numbers_sprite, window_controller):

        # Compute alpha based on lifespan
        alpha = ( self.lifespan / float(NUMBERCLE_LIFESPAN) ) - 0.25 # max of 0.75

        # Don't go below 0
        if (alpha < 0):
            alpha = 0

        window_controller.get_gfx_controller().draw_sprite(sx + self.get_x(), sy + self.get_y(), NUMBERCLE_WIDTH, NUMBERCLE_HEIGHT, numbers_sprite, frame = self.number, degrees = self.degrees, gl_color = (1, 1, 1, alpha))
