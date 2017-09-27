from code.controllers.intervalcontroller import IntervalController

from code.render.glfunctions import draw_texture_with_texture_coords

from code.utils.common import intersect

from code.constants.common import TILE_WIDTH, TILE_HEIGHT, MAGIC_WALL_TILE_INDEX_DEFAULT, MAGIC_WALL_TILE_INDEX_SPIKES_LEFT, MAGIC_WALL_TILE_INDEX_SPIKES_RIGHT, MAGIC_WALL_BRICK_WIDTH, MAGIC_WALL_BRICK_HEIGHT, MAGIC_WALL_BRICK_DELAY, MAGIC_WALL_BRICK_DROP_HEIGHT, DIR_LEFT, DIR_RIGHT, COLLISION_NONE

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.death import DEATH_BY_VAPORIZATION # Magic wall kills an entity this way (?)


class MagicWallBrick:

    def __init__(self, delay, x, y, w, h, dest_x, dest_y, texture_coords):

        # Delay before processing / drawing (for a brick-by-brick effect)
        self.delay = delay

        # Initial screen position
        self.x = x
        self.y = y

        # Where do we go?
        self.dest_x = dest_x
        self.dest_y = dest_y

        # Has the brick reached its destination?
        self.ready = False

        # Speed
        self.dx = 0
        self.dy = 2.5


        # Dimension sfor this brick component
        self.width = w
        self.height = h


        # Texture coordinates for this brick.  Why re-fetch them every time?
        self.texture_coords = texture_coords


        # Alpha control
        self.alpha_controller = IntervalController(
            interval = 0.0,
            target = 1.0,
            speed_in = 0.05,
            speed_out = 0.05
        )


    def get_x(self):

        return int(self.x)

    def get_y(self):

        return int(self.y)


    def process(self):

        if (self.delay > 0):

            self.delay -= 1

        else:

            # Process alpha
            self.alpha_controller.process()

            # Honestly, x-axis never changes.  Let's just do y-axis...
            self.y += self.dy

            # Don't overshoot
            if (self.y >= self.dest_y):

                self.y = self.dest_y

                # We're home!
                self.ready = True


    def draw(self, sx, sy, tilesheet_sprite, alpha):

        if (self.delay == 0):

            draw_texture_with_texture_coords(tilesheet_sprite.get_texture_id(), self.texture_coords, int(sx + self.get_x()), int(sy + self.get_y()), self.width, self.height, gl_color = (1, 1, 1, self.alpha_controller.get_interval()))



class MagicWall:

    def __init__(self, tx, ty, direction, lifespan, has_spikes, covered_tile_index):

        # We have to wait for the map rendering loop to compute the various bricks (using tilesheet data)
        self.setup_complete = False

        # Wall state
        self.state = STATUS_ACTIVE

        # What was the previous tile value of the location we are placing
        # the magic wall on?  For instance, if we placed it over a fence,
        # that's valid, but we need to know to revert to the fence afterward...
        self.covered_tile_index = covered_tile_index

        # How long will the wall last (after full construction)?
        self.lifespan = lifespan

        # Tile coordinates
        self.tx = tx
        self.ty = ty

        # Direction (so we know which side to put spikes on if applicable)
        self.direction = direction

        # Does it have spikes?
        self.has_spikes = has_spikes


        # When the wall is forming, we will display a series of "particles"
        # falling into place, as if composing a brick wall.
        self.bricks = []

        # Have all of the bricks fallen into place?
        self.ready = False


    def get_tile_index(self):

        tile_index = MAGIC_WALL_TILE_INDEX_DEFAULT

        if (self.has_spikes):

            if (self.direction == DIR_LEFT):
                tile_index = MAGIC_WALL_TILE_INDEX_SPIKES_LEFT

            elif (self.direction == DIR_RIGHT):
                tile_index = MAGIC_WALL_TILE_INDEX_SPIKES_RIGHT

        return tile_index


    def get_rect(self):

        return ( (self.tx * TILE_WIDTH), (self.ty * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT )


    def setup_bricks(self, tilesheet_sprite):

        # Bricks per row
        per_row = int(TILE_WIDTH / MAGIC_WALL_BRICK_WIDTH)

        # Total rows
        total_rows = int(TILE_HEIGHT / MAGIC_WALL_BRICK_HEIGHT)


        # Real quick, let's get the texture coordinates for the tile that will represent this magic wall...
        # We'll base the sub-texture coordinates for each brick on this initial data...
        texture_coords = tilesheet_sprite.get_texture_coordinates( self.get_tile_index() )

        # You know, let's also pre-calculate the "step" value we'll take as we go through
        # each of the bricks in the grid...
        (tstepX, tstepY) = (
            (float(MAGIC_WALL_BRICK_WIDTH) / float(TILE_WIDTH)) * texture_coords[2],
            (float(MAGIC_WALL_BRICK_HEIGHT) / float(TILE_HEIGHT)) * texture_coords[3]
        )


        for y in range(0, total_rows):

            # We're going to have one extra brick on "odd" rows to create a stagger effect...
            odd_row = (y % 2) == 1

            for x in range(0, (per_row + int(odd_row))):

                # Calculate the final position of this brick...
                (dest_x, dest_y) = (
                    (x * MAGIC_WALL_BRICK_WIDTH) - ( int(odd_row) * int(MAGIC_WALL_BRICK_WIDTH / 2) ),
                    (y * MAGIC_WALL_BRICK_HEIGHT)
                )

                # Where will we spawn the brick?
                (px, py) = (
                    x * MAGIC_WALL_BRICK_WIDTH,
                    (y * MAGIC_WALL_BRICK_HEIGHT)- MAGIC_WALL_BRICK_DROP_HEIGHT
                )


                # Determine the size of this brick...
                (w, h) = (
                    MAGIC_WALL_BRICK_WIDTH,
                    MAGIC_WALL_BRICK_HEIGHT
                )


                # Let's figure the sub-texture coordinates we'll use for this brick
                sub_texture_coords = (
                    texture_coords[0] + (x * tstepX),
                    texture_coords[1] + ( ((total_rows - 1) - y) * tstepY),
                    tstepX,
                    tstepY
                )

                # Darned odd (staggered) rows!
                if (odd_row):

                    # Left brick, only show left half...
                    if (x == 0):

                        (w, h) = (
                            int(w / 2),
                            h
                        )

                        sub_texture_coords = (
                            texture_coords[0] + (x * tstepX),
                            texture_coords[1] + ( ((total_rows - 1) - y) * tstepY),
                            float(tstepX / 2.0),
                            tstepY
                        )

                    # Right brick, only show right half...
                    elif (x == (per_row)):

                        # Right-edge staggered brick must be moved over by half a brick width...
                        px -= int(w / 2)

                        (w, h) = (
                            int(w / 2),
                            h
                        )

                        sub_texture_coords = (
                            texture_coords[0] + (x * tstepX) - tstepX + float(tstepX / 2.0),
                            texture_coords[1] + ( ((total_rows - 1) - y) * tstepY),
                            float(tstepX / 2.0),
                            tstepY
                        )

                    else:

                        px -= int(w / 2)

                        sub_texture_coords = (
                            texture_coords[0] + (x * tstepX) - float(tstepX / 2.0),
                            texture_coords[1] + ( ((total_rows - 1) - y) * tstepY),
                            tstepX,
                            tstepY
                        )


                # Lastly, calculate the delay for this block.  Begin by computing how many blocks
                # appear prior to the current row.
                preceding_block_count = 0

                # Check any prior row...
                for row_y in range(0, (total_rows - y - 1)):

                    # Increase block count, accounting for staggered rows (which have an extra block)
                    preceding_block_count += per_row + (row_y % 2)

                # The delay will account for all preceding blocks plus the current x position of this brick...
                delay = (preceding_block_count * MAGIC_WALL_BRICK_DELAY) + (x * MAGIC_WALL_BRICK_DELAY)


                # Create the brick already!
                self.bricks.append(
                    MagicWallBrick(delay, px, py, w, h, dest_x, dest_y, sub_texture_coords)
                )


    # Sometimes the map will destroy the magic wall just-like-that (e.g. planar shift) on some map m
    def destroy_on_map(self, m):

        # Disable
        self.state = STATUS_INACTIVE

        # Safety
        if ( m.master_plane.get_tile(self.tx, self.ty) == self.get_tile_index() ):

            m.master_plane.set_tile(self.tx, self.ty, 0)

        # Create a particle effect based on the magic wall's tile index value
        m.create_particle_effect((self.tx * TILE_WIDTH), (self.ty * TILE_HEIGHT), self.get_tile_index())


    def process(self, control_center, universe):

        # Fetch active map
        m = universe.get_active_map()


        # Not ready yet?  Let's keep filling in blocks...
        if (not self.ready):

            # For now...
            self.ready = True

            for brick in self.bricks:

                brick.process()

                # All bricks must be in place before we're done...
                if (not brick.ready):

                    self.ready = False


            # Whether we're ready or not, we want to check the tile we placed the magic wall on.
            # If we placed it on a previously-dug tile and the tile has now returned, then the
            # tile "wins" and we must destroy the magic wall immediately.
            #if (m.master_plane.get_tile(self.tx, self.ty) != 0):
            if ( not (m.master_plane.check_collision(self.tx, self.ty, strictly_within_level = True) in (COLLISION_NONE,)) ):

                # Disable before we even finished building...
                self.state = STATUS_INACTIVE

                # Don't touch the master plane!

                # Particle effect
                m.create_particle_effect((self.tx * TILE_WIDTH), (self.ty * TILE_HEIGHT), self.get_tile_index())


            # Ready, ready?
            if (self.ready):

                # Set the map's tilemap data to a "magic wall" tile for the moment...
                m.master_plane.set_tile(self.tx, self.ty, self.get_tile_index())


                # Now that the thing is ready, we need to destroy any entity that collides with this tile...
                for entity in m.get_bombable_entities():

                    # Don't test against ourself, no matter what!
                    if ( not (entity == self) ):

                        if ( intersect(self.get_rect(), entity.get_rect()) ):

                            entity.queue_death_by_cause(DEATH_BY_VAPORIZATION)

        # If it's ready, then we'll lower the lifespan until it's gone...
        else:

            self.lifespan -= 1

            # If the tile value at this location has changed away from the magic wall's tile value,
            # that indicates that we placed a magic wall on top of a previously-dug tile, and the tile
            # has finished returning.  In this case, we must destroy the magic wall (without returning
            # the tile value to 0!) and have done with it altogether...
            if (m.master_plane.get_tile(self.tx, self.ty) != self.get_tile_index()):

                # Disable
                self.state = STATUS_INACTIVE

                # DO NOT do anything to the master plane

                # Create a particle effect; the wall has been destroyed by a tile fill.
                m.create_particle_effect((self.tx * TILE_WIDTH), (self.ty * TILE_HEIGHT), self.get_tile_index())

            # Game over for this magic wall?
            elif (self.lifespan <= 0):

                # Disable
                self.state = STATUS_INACTIVE

                # We must return the tile index on the map to its previos value at this location.
                # That might be 0 (if we placed the wall where we had dug a tile), or it might be
                # a fence, or some other mask layer type tile.
                m.master_plane.set_tile(self.tx, self.ty, self.covered_tile_index)

                # Create a particle effect based on the magic wall's tile index value
                m.create_particle_effect((self.tx * TILE_WIDTH), (self.ty * TILE_HEIGHT), self.get_tile_index())


    def draw(self, sx, sy, tilesheet_sprite, alpha):

        if (not self.setup_complete):

            self.setup_bricks(tilesheet_sprite)
            self.setup_complete = True


        (x, y) = (
            self.tx * TILE_WIDTH,
            self.ty * TILE_HEIGHT
        )

        for brick in self.bricks:

            brick.draw(x + sx, y + sy, tilesheet_sprite, alpha)

