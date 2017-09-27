from code.utils.common import log, log2, rect_within_rect

from code.constants.common import CAMERA_SPEED, MIN_MAP_SCROLL_X, MIN_MAP_SCROLL_Y, MAX_PERIMETER_SCROLL_X, MAX_PERIMETER_SCROLL_Y, SCREEN_WIDTH, SCREEN_HEIGHT, TILE_WIDTH, TILE_HEIGHT

class Camera:

    def __init__(self, x = 0, y = 0):

        # Position
        self.x = x
        self.y = y

        # Target
        self.target_x = x
        self.target_y = y


        # We can lock the camera to prevent position / target changes
        self.lock_count = 0


        # Need a viewport for focusing / centering calculations
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT

        # We'll specify a region in which the camera can cleanly move.
        # If it leaves the given region, we'll have to redo prerendering data.
        self.prerender_bounds = (0, 0, 0, 0)

        # I want to keep track of what position the camera held when we created the prerender.
        # I'll use this to determine parallax offset calculations.
        self.prerender_location = (0, 0)

        # If the camera leaves that region (at all),
        # then we'll have to mark it as dirty.
        self.dirty = False


    # Configure
    def configure(self, options):

        if ( "target-x" in options ):
            self.target_x = int( options["target-x"] )

        if ( "target-y" in options ):
            self.target_y = int( options["target-y"] )

        if ( "width" in options ):
            self.set_width( int( options["width"] ) )

        if ( "height" in options ):
            self.set_height( int( options["height"] ) )

        if ( "prerender-bounds" in options ):
            self.prerender_bounds = options["prerender-bounds"]

        if ( "prerender-location" in options ):
            self.prerender_location = options["prerender-location"]

        if ( "dirty" in options ):
            self.dirty = ( int( options["dirty"] ) == 1 )


        # For chaining
        return self


    # Lock the camera
    def lock(self):

        self.lock_count += 1


    # Unlock the camera
    def unlock(self):

        self.lock_count -= 1

        # Stay positive
        if (self.lock_count < 0):

            self.lock_count = 0


    # Check lock status
    def is_locked(self):

        return (self.lock_count > 0)


    def set_width(self, width):

        self.width = width


    def get_width(self):

        return self.width


    def set_height(self, height):

        self.height = height


    def get_height(self):

        return self.height


    def position(self, x, y):

        # Not while locked
        if ( not self.is_locked() ):

            self.x = x
            self.y = y


    # Is the camera dirty?
    def is_dirty(self):

        return self.dirty


    # Retrieve parallax-adjusted coordinates for a given camera location
    def get_parallax_offsets_at_location(self, x, y, parallax = 1.0):

        # Calculate magnitude first
        (px, py) = (
            int( abs(x) / parallax ) - abs(x),
            int( abs(y) / parallax ) - abs(y)
        )

        # Adjust vector direction depending on which side of each axis we're on
        if ( x < 0 ):
            px *= -1

        if ( y < 0 ):
            py *= -1

        # Return offsets
        return (px, py)


    # m = map
    def focus(self, entity, m):

        # Not while locked
        if ( not self.is_locked() ):

            # Map dimensions
            (map_width, map_height) = (
                (m.width * TILE_WIDTH),
                (m.height * TILE_HEIGHT)
            )

            # Raw universal map coordinates
            (map_x, map_y) = (
                (m.x * TILE_WIDTH),
                (m.y * TILE_HEIGHT)
            )

            # Let us assume we will center the camera at the map's origin...
            (cx, cy) = (
                map_x + int( (m.width * TILE_WIDTH) / 2),
                map_y + int( (m.height * TILE_HEIGHT) / 2)
            )

            # The offset coordinates for the camera would, then equate to...
            (sx, sy) = (
                cx - int( self.get_width() / 2 ),
                cy - int( self.get_height() / 2 )
            )


            # If the current map's size fits completely within the allowed perimeter scroll, we will simply accept
            # those offset coordinates as the target; the map will never need any scrolling, due to its small size.
            if ( map_width <= self.get_width() - (2 * MAX_PERIMETER_SCROLL_X) ):
                self.target_x = sx

            # Otherwise, we're first going to make sure the camera keeps the active level in easy view...
            else:

                # Calculate universal entity coordinate
                px = map_x + entity.get_x()


                # If the distance between the entity's left edge and the left camera border is too small, we will want to pan left...
                if ( (px - int(self.x)) < MIN_MAP_SCROLL_X ):
                    self.target_x = px - MIN_MAP_SCROLL_X

                    # Ensure that the focus remains chiefly on the active map...
                    if ( (map_x - self.target_x) > MAX_PERIMETER_SCROLL_X ):
                        self.target_x = map_x - MAX_PERIMETER_SCROLL_X

                # Similarly test the right edge...
                elif ( ((int(self.x) + self.get_width()) - (px + entity.width)) < MIN_MAP_SCROLL_X ):
                    self.target_x = MIN_MAP_SCROLL_X + (px + entity.width) - self.get_width()

                    # Ensure that the focus remains chiefly on the active map...
                    if ( (self.target_x + self.get_width()) - (map_x + map_width) > MAX_PERIMETER_SCROLL_X ):
                        self.target_x = MAX_PERIMETER_SCROLL_X + (map_x + map_width) - self.get_width()


                # Looks like the camera's good right where it's at...
                else:
                    self.x = int(self.x)
                    self.target_x = self.x



                # Ensure that the focus remains chiefly on the active map...
                if ( (map_x - self.target_x) > MAX_PERIMETER_SCROLL_X ):
                    self.target_x = map_x - MAX_PERIMETER_SCROLL_X

                elif ( (self.target_x + self.get_width()) - (map_x + map_width) > MAX_PERIMETER_SCROLL_X ):
                    self.target_x = MAX_PERIMETER_SCROLL_X + (map_x + map_width) - self.get_width()


            # If the current map's size fits completely within the allowed perimeter scroll, we will simply accept
            # those offset coordinates as the target; the map will never need any scrolling, due to its small size.
            if ( map_height <= self.get_height() - (2 * MAX_PERIMETER_SCROLL_Y) ):
                self.target_y = sy

            # Otherwise, we're first going to make sure the camera keeps the active level in easy view...
            else:

                # Calculate universal entity coordinate
                py = map_y + entity.get_y()


                # If the distance between the entity's left edge and the left camera border is too small, we will want to pan left...
                if ( (py - int(self.y)) < MIN_MAP_SCROLL_Y ):
                    self.target_y = py - MIN_MAP_SCROLL_Y

                    # Ensure that the focus remains chiefly on the active map...
                    if ( (map_y - self.target_y) > MAX_PERIMETER_SCROLL_Y ):
                        self.target_y = map_y - MAX_PERIMETER_SCROLL_Y

                # Similarly test the right edge...
                elif ( ((int(self.y) + self.get_height()) - (py + entity.height)) < MIN_MAP_SCROLL_Y ):
                    self.target_y = MIN_MAP_SCROLL_Y + (py + entity.height) - self.get_height()

                    # Ensure that the focus remains chiefly on the active map...
                    if ( (self.target_y + self.get_height()) - (map_y + map_height) > MAX_PERIMETER_SCROLL_Y ):
                        self.target_y = MAX_PERIMETER_SCROLL_Y + (map_y + map_height) - self.get_height()


                # Looks like the camera's good right where it's at...
                else:
                    self.y = int(self.y)
                    self.target_y = self.y



                # Ensure that the focus remains chiefly on the active map...
                if ( (map_y - self.target_y) > MAX_PERIMETER_SCROLL_Y ):
                    self.target_y = map_y - MAX_PERIMETER_SCROLL_Y

                if ( (self.target_y + self.get_height()) - (map_y + map_height) > MAX_PERIMETER_SCROLL_Y ):
                    self.target_y = MAX_PERIMETER_SCROLL_Y + (map_y + map_height) - self.get_height()


    def center_on_entity_within_map(self, entity, m):

        # Not while locked!
        if ( not self.is_locked() ):

            # Raw universal map coordinates
            (map_x, map_y) = (
                (m.x * TILE_WIDTH),
                (m.y * TILE_HEIGHT)
            )

            self.target_x = (entity.get_x() + int(entity.width / 2)) - int( self.get_width() / 2 ) + map_x
            self.target_y = (entity.get_y() + int(entity.height / 2)) - int( self.get_height() / 2 ) + map_y


    def pan(self, speed_x, speed_y):

        if (self.x < self.target_x):

            # Pan right
            self.x += speed_x

            # Don't overshoot
            if (self.x > self.target_x):
                self.x = self.target_x

        elif (self.x > self.target_x):

            # Pan left
            self.x -= speed_x

            # Don't overshoot
            if (self.x < self.target_x):
                self.x = self.target_x


        if (self.y < self.target_y):

            # Pan down
            self.y += speed_y

            # Don't overshoot
            if (self.y > self.target_y):
                self.y = self.target_y

        elif (self.y > self.target_y):

            # Pan up
            self.y -= speed_y

            # Don't overshoot
            if (self.y < self.target_y):
                self.y = self.target_y


    def zap(self):

        # Not while locked
        if ( not self.is_locked() ):

            self.x = self.target_x
            self.y = self.target_y


    def process(self, control_center):

        # Check to see if we've exceeded our prerender bounds...
        if ( not self.is_dirty() ):

            # Dirty yet?
            if ( not rect_within_rect(
                (self.x, self.y, self.width, self.height),
                self.prerender_bounds
            ) ):

                # Dirty now
                self.dirty = True

