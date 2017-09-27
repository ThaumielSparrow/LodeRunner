import random

from code.render.glfunctions import GLSpritesheet
from code.render.glfunctions import draw_sprite, set_visible_region_on_texture, clip_backbuffer, draw_rotated_texture_with_texture_coords, delete_texture

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_EXPLODER_PIECE_INITIAL_GRAVITY, SCREEN_EXPLODER_PIECE_GRAVITY_DELAY, SCREEN_EXPLODER_PIECE_MAX_GRAVITY

class ScreenExploderPiece:

    def __init__(self, x, y, size, texture_coords):

        # State
        self.state = True

        # Position
        self.x = x
        self.y = y

        # Piece size
        self.size = size

        # Remember texture coordinates
        self.texture_coords = texture_coords

        # Random speed
        self.dx = random.randint(2, 6)

        if (random.randint(1, 10) >= 5):
            self.dx *= -1

        # Gravity
        self.gravity = -1 * random.randint(1, 8)

        # Tracking
        self.gravity_interval = 0
        self.gravity_interval_max = SCREEN_EXPLODER_PIECE_GRAVITY_DELAY

        # Rotation
        self.degrees = 0

        self.rotation_speed = random.randint(2, 5)

        if (self.x < int(SCREEN_WIDTH / 2)):
            self.rotation_speed *= -1


    def process(self):

        # Do gravity
        self.gravity_interval += 1

        if (self.gravity_interval >= self.gravity_interval_max):

            self.gravity_interval = 0
            self.gravity += 1

            if (self.gravity >= SCREEN_EXPLODER_PIECE_MAX_GRAVITY):
                self.gravity = SCREEN_EXPLODER_PIECE_MAX_GRAVITY


        # Do rotation
        self.degrees += self.rotation_speed

        # Wraparound
        if (self.degrees >= 360):
            self.degrees -= 360

        elif (self.degrees < 0):
            self.degrees += 360


        # Lateral movement
        self.x += self.dx

        # Gravity movement
        self.y += self.gravity



    def draw(self, texture_id, alpha = None):

        draw_rotated_texture_with_texture_coords(self.degrees, texture_id, self.texture_coords, self.x, self.y, self.size, self.size, gl_color = (1, 1, 1, 1))


class ScreenExploder:

    def __init__(self, piece_size):

        # Track the texture id we get when we cap the screen
        self.texture_id = None

        # Texture dimensions
        self.texture_size = 0

        # The size of each piece (square pieces)
        self.piece_size = piece_size

        # A collection of all pieces and their locations...
        self.pieces = []


    # Begin the explosion
    def explode(self):

        # If we previously had a texture id, then let's release it...
        if (self.texture_id != None):

            delete_texture(self.texture_id)

            # We're done with it for the moment...
            self.texture_id = None


        # Grab the framebuffer
        (self.texture_id, self.texture_size, unused) = clip_backbuffer(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Hide any offscreen pixels
        set_visible_region_on_texture(self.texture_id, self.texture_size, self.texture_size, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # Populate a collection of pieces
        self.pieces = []

        for y in range(0, int(SCREEN_HEIGHT / self.piece_size)):

            for x in range(0, int(SCREEN_WIDTH / self.piece_size)):

                # Tile index for this piece...
                tile = (y * int(SCREEN_WIDTH / self.piece_size)) + x

                # initial screen location (also, source location throughout)
                (px, py) = (
                    x * self.piece_size,
                    y * self.piece_size
                )

                # Create a new screen piece...
                self.pieces.append(
                    ScreenExploderPiece(
                        px,
                        py,
                        self.piece_size,
                        self.get_texture_coordinates(x, y)
                    )
                )


    # Get a piece's texture coordinates
    def get_texture_coordinates(self, x, y):

        tstep = float(self.piece_size) / float(self.texture_size)

        (tu, tv) = (
            x * tstep,
            1.0 - (y * tstep) - tstep
        )

        return (tu, tv, tstep, tstep)


    # Process pieces
    def process(self):

        for piece in self.pieces:

            piece.process()


    # Render effect
    def draw(self):

        for piece in self.pieces:

            piece.draw(self.texture_id)
