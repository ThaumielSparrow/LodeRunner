from code.render.glfunctions import *
from code.constants.paths import GFX_PATH # The only one we need here 

class GfxController:

    def __init__(self, render_offset_x, render_offset_y, visibility_region):

        # Calibrate the controller to render from a given base
        self.render_offset_x = render_offset_x
        self.render_offset_y = render_offset_y

        # Track the game's default visibility region
        self.visibility_region = visibility_region


        # The gfx controller can save various spritesheets, keyed by a given name
        self.spritesheets = {}


        # The gfx controller houses all of the game's built-in sprite data (tilesheets, animations, etc.)
        self.graphics = {}


    def delete_texture(self, texture_id):

        delete_texture(texture_id)


    def copy_texture_to_texture(self, texture_id1, texture_id2, w, h):

        copy_texture_to_texture(texture_id1, texture_id2, w, h)


    def clone_texture(self, texture_id1, w, h):

        return clone_texture(texture_id1, w, h)


    def replace_color_on_texture(self, texture_id, w, h, color1, color2):

        replace_color_on_texture(texture_id, w, h, color1, color2)


    # Load (or reload) image assets
    def load_image_assets(self):

        # Create a sprite for the mouse
        self.graphics["cursor"] = self.create_spritesheet( os.path.join(GFX_PATH, "mouse.png"), 32, 32, first_pixel_transparent = False)

        # Create a "tilesheet" (just a spritesheet that has all of the tiles)
        self.graphics["tilesheet"] = self.create_spritesheet( os.path.join(GFX_PATH, "tileset3b.png"), 24, 24, first_pixel_transparent = False )


        # Various entity sprites (player, bad guys, bombs, levers, etc.)
        self.graphics["sprites"] = {
            GENUS_PLAYER: {
                "normal": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.png"), 24, 24 ),
                "disguised": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.png"), 24, 24, first_pixel_transparent = False ),
                "netplayer1": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.png"), 24, 24 ),
                "netplayer2": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.png"), 24, 24 ),
                "netplayer3": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.png"), 24, 24 ),
                "netplayer4": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.png"), 24, 24 ),
                "simple": self.create_spritesheet( os.path.join(GFX_PATH, "player1m.simple.png"), 24, 24 )
            },
            GENUS_ENEMY: self.create_spritesheet( os.path.join(GFX_PATH, "enemy1.png"), 24, 24, first_pixel_transparent = False ),
            GENUS_NPC: {
                "generic": self.create_spritesheet( os.path.join(GFX_PATH, "player1c.png"), 24, 24 ),
                "terminal": self.create_spritesheet( os.path.join(GFX_PATH, "terminal1.png"), 24, 24 ),
                "terminal.lock": self.create_spritesheet( os.path.join(GFX_PATH, "terminal1.lock.png"), 12, 12 ),
                "indicator-arrow": self.create_spritesheet( os.path.join(GFX_PATH, "arrow1.png"), 24, 24 )
            },
            GENUS_HOLOGRAM: {
                "generic": self.create_spritesheet( os.path.join(GFX_PATH, "player1c.png"), 24, 24 )
            },
            GENUS_LEVER: self.create_spritesheet( os.path.join(GFX_PATH, "lever1.png"), 24, 24 ),
            GENUS_BOMB: self.create_spritesheet( os.path.join(GFX_PATH, "bomb1.png"), 24, 24 ),
            "fill-patterns:history": {
                1: self.create_spritesheet( os.path.join(GFX_PATH, "fill_history1.png"), 24, 24, first_pixel_transparent = False ),
                2: self.create_spritesheet( os.path.join(GFX_PATH, "fill_history2.png"), 24, 24, first_pixel_transparent = False ),
                3: self.create_spritesheet( os.path.join(GFX_PATH, "fill_history3.png"), 24, 24, first_pixel_transparent = False ),
                4: self.create_spritesheet( os.path.join(GFX_PATH, "fill_history4.png"), 24, 24, first_pixel_transparent = False ),
                5: self.create_spritesheet( os.path.join(GFX_PATH, "fill_history5.png"), 24, 24, first_pixel_transparent = False )
            },
            "fill-patterns:mask": {
                1: self.create_spritesheet( os.path.join(GFX_PATH, "fill_mask1.png"), 24, 24, first_pixel_transparent = False ),
                2: self.create_spritesheet( os.path.join(GFX_PATH, "fill_mask2.png"), 24, 24, first_pixel_transparent = False ),
                3: self.create_spritesheet( os.path.join(GFX_PATH, "fill_mask3.png"), 24, 24, first_pixel_transparent = False ),
                4: self.create_spritesheet( os.path.join(GFX_PATH, "fill_mask4.png"), 24, 24, first_pixel_transparent = False ),
                5: self.create_spritesheet( os.path.join(GFX_PATH, "fill_mask5.png"), 24, 24, first_pixel_transparent = False )
            },
            "numbercles": self.create_spritesheet( os.path.join(GFX_PATH, "numbercles.png"), 12, 12 ),
            GENUS_RESPAWN_PLAYER1: self.create_spritesheet( os.path.join(GFX_PATH, "respawn.player1.png"), 24, 24 ),
            GENUS_RESPAWN_PLAYER2: self.create_spritesheet( os.path.join(GFX_PATH, "respawn.player2.png"), 24, 24 ),
            GENUS_RESPAWN_PLAYER: self.create_spritesheet( os.path.join(GFX_PATH, "heart1.png"), 24, 24 ),
            GENUS_RESPAWN_ENEMY: self.create_spritesheet( os.path.join(GFX_PATH, "respawn.enemy.png"), 24, 24 ),
            GENUS_GOLD: self.create_spritesheet( os.path.join(GFX_PATH, "gold2.png"), 24, 24 ),
            "skill-icons": self.create_spritesheet( os.path.join(GFX_PATH, "skill_icons.png"), 24, 24 ),
            "hud-icons": self.create_spritesheet( os.path.join(GFX_PATH, "hud_icons.png"), 24, 24 ),
            "iconset1": self.create_spritesheet( os.path.join(GFX_PATH, "iconset1.png"), 24, 24 )
        }


    # Unload image assets
    def unload_image_assets(self):

        # Release all simple textures
        for key in ("cursor", "tilesheet"):

            # Release
            self.graphics[key].unload()

        # Loop additional sprite categories
        for category in self.graphics["sprites"]:

            # If we have a hash of data on this key, then we'll loop into the hash
            if ( type( self.graphics["sprites"][category] ) == type({}) ):

                # Loop children
                for key in self.graphics["sprites"][category]:

                    # Release
                    self.graphics["sprites"][category][key].unload()

            # Otherwise, we'll release texture
            else:
                self.graphics["sprites"][category].unload()


        # Clear hash
        self.graphics.clear()


    # Get a particular graphic object
    def get_graphic(self, name):

        # Validate key
        if (name in self.graphics):

            # Return graphic
            return self.graphics[name]

        else:
            return None


    # Create a GLSpritesheet
    def create_spritesheet(self, filepath, width, height, first_pixel_transparent = True):

        # Create GLSpritesheet object
        return GLSpritesheet(filepath, width, height, first_pixel_transparent)


    # Add a new spritesheet (tracked by name)
    def add_spritesheet_with_name(self, name, filepath, width, height, first_pixel_transparent = True):

        # Don't load it twice
        if ( not (name in self.spritesheets) ):

            # Add spritesheet
            self.spritesheets[name] = self.create_spritesheet(filepath, width, height, first_pixel_transparent)


    # Get a spritesheet by name
    def get_spritesheet_by_name(self, name):

        # Validate
        if (name in self.spritesheets):

            # Return
            return self.spritesheets[name]

        # Couldn't find it
        else:

            return None


    def draw_textured_row(self, x, y, tilesheet_sprite, tile_values = [], gl_color = None, min_x = 0, max_x = SCREEN_WIDTH, min_y = 0, max_y = SCREEN_HEIGHT, scale = 1.0):#window_x = 0, window_y = 0):

        # This one's a little funky.  We pretend to draw at plain (x, y); the function
        # itself adjusts the gl cursor to draw everything where we want it.
        draw_textured_row(x, y, tilesheet_sprite, tile_values, gl_color, min_x = (self.render_offset_x + min_x), max_x = (self.render_offset_x + max_x), min_y = (self.render_offset_y + min_y), max_y = (self.render_offset_y + max_y), scale = scale)#window_x = 0, window_y = 0):


    def draw_particle(self, x, y, index_x, index_y, degrees, tile, tilesheet_sprite, color):

        draw_particle(self.render_offset_x + x, self.render_offset_y + y, index_x, index_y, degrees, tile, tilesheet_sprite, color)


    def draw_fill_pattern(self, x, y, tile, tilesheet_sprite, frame, fill_sprite, gl_color = None):

        draw_fill_pattern(self.render_offset_x + x, self.render_offset_y + y, tile, tilesheet_sprite, frame, fill_sprite, gl_color)


    def draw_texture(self, texture, x, y, w, h, color = (1, 1, 1, 1)):

        draw_texture(texture, self.render_offset_x + x, self.render_offset_y + y, w, h, color)


    def draw_texture_with_gradient(self, texture, x, y, w, h, color1 = (1, 1, 1, 1), color2 = (1, 1, 1, 1)):

        draw_texture_with_gradient(texture, self.render_offset_x + x, self.render_offset_y + y, w, h, color1, color2)


    def draw_texture_with_texture_coords(self, texture_id, texture_coords, x, y, w, h, gl_color = (1, 1, 1, 1), degrees = 0):

        draw_texture_with_texture_coords(texture_id, texture_coords, self.render_offset_x + x, self.render_offset_y + y, w, h, gl_color, degrees)


    def draw_rotated_texture_with_texture_coords(self, degrees, texture_id, texture_coords, x, y, w, h, gl_color = (1, 1, 1, 1)):

        draw_rotated_texture_with_texture_coords(degrees, texture_id, texture_coords, self.render_offset_x + x, self.render_offset_y + y, w, h, gl_color)


    def draw_sprite(self, x, y, w, h, sprite, frame = 0, gl_color = None, degrees = 0, hflip = False, vflip = False, working_texture = None, scale = 1.0):

        draw_sprite(x, y, w, h, sprite, frame, gl_color, degrees, visibility_region = self.visibility_region, hflip = hflip, vflip = vflip, working_texture = working_texture, scale = scale)


    def apply_greyscale_effect_to_texture(self, texture_id, w, h, percent = 1.0):

        apply_greyscale_effect_to_texture(texture_id, w, h, percent)


    def apply_greyscale_effect_to_screen(self, x, y, w, h, percent = 1.0):

        apply_greyscale_effect_to_screen(x, y, w, h, percent)


    def apply_radial_greyscale_effect_to_screen(self, x, y, w, h, percent, angle):

        apply_radial_greyscale_effect_to_screen(x, y, w, h, percent, angle)
