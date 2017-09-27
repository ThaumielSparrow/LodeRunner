import pygame
from pygame.locals import *

#from OpenGL.GL import *
#from OpenGL.GLU import *

import os
import sys

import math

import copy

import re
import random

import platform
import struct

from ctypes import *

from code.utils.common import intersect, increment_glcolor_by_n_gradient_steps, multiply_glcolor_alpha_by_coefficient, set_alpha_for_rgb, rgb_to_glcolor, rgb_to_hex, log, log2, logn

from code.constants.common import *


# Local constant
VALID_CHARACTER_CODES = range(33, 127) + range(160, 166) + [243]


#asdfasdfasd = cdll.LoadLibrary("./dll2.dll")
#gl = cdll.LoadLibrary("libGL.so")
#glLoadIdentity = gl.glLoadIdentity
#print gl
#print glLoadIdentity
#GL = cdll.LoadLibrary("./dllx.dll")


# Scope
#GL = None
#GLExt = None

GL = None
GLExt = None


# Assume 32 bit
bit_size = 32

# Check for 64 bit
if ( struct.calcsize("P") == 8 ):

    # This is a 64 bit environment
    bit_size = 64


# Windows?
# Currently I am loading only 32, compiled py2exe through 32bit python (?)
if ( platform.system().lower() == "windows" ):

    # Load windows DLLs
    GL = cdll.LoadLibrary(
        os.path.join("dlls", "win32", "render.dll")
    )

    GLExt = cdll.LoadLibrary(
        os.path.join("dlls", "win32", "renderext.dll")
    )

# Assume linux (for now)
else:

    # Load linux DLLs
    GL = cdll.LoadLibrary(
        os.path.join("dlls", "linux%d" % bit_size, "render.dll")
    )

    GLExt = cdll.LoadLibrary(
        os.path.join("dlls", "linux%d" % bit_size, "renderext.dll")
    )

# Reference to C-compiled library of gl rendering functions
#GL = cdll.LoadLibrary( os.path.join(""./gltest1dll.dll")
#GL.asdfinit()
# **Shader functions, let's name these dll / GL things a little more clearly sometime...
#GLExt = cdll.LoadLibrary("./dll2.dll")



##############################################################
## OPENGL HELPER FUNCTIONS

 
def render_init(w, h, fullscreen = False):

    # Finds the smallest available resolution that fits the desired viewfield.
    log( "desired resolution:  ", w, h )

    pygame.init()

    return set_video_mode(w, h, fullscreen)


def set_video_mode(w, h, fullscreen):

    modelist = pygame.display.list_modes()
    nextmode = []
    for l in modelist:
        if l[0]>=w and l[1]>=h:
            nextmode.append(l)
    bestx, besty = -1,-1
    for l in nextmode:
        if bestx==-1 or bestx>=l[0]:
            if besty==-1 or besty>=l[1]:
                bestx, besty = l[0],l[1]
 
    log( "best resolution: ",bestx, besty )
 
    initializeDisplay(bestx, besty, fullscreen)


    # Debug
    """
    #s = glGetString(GL_EXTENSIONS)
    #print "\n".join( s.split(" ") )
    #print "GL Version:  ", glGetString(GL_VERSION)
    #print 5/0
    """


    return (bestx, besty)

    #return newList


def initializeDisplay(w, h, fullscreen = False):

    #x = 2
    #log( "initializeDisplay stencil size setting:  ", x )

    pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 1)


    if (fullscreen == True):
        pygame.display.set_mode((w, h), pygame.HWSURFACE | pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN)

    else:
        pygame.display.set_mode((w,h), pygame.OPENGL|pygame.DOUBLEBUF)


    GL.csetup_opengl(w, h)


    log( "\tconfirmed after as:  ", pygame.display.gl_get_attribute(pygame.GL_STENCIL_SIZE) )

    # Draw on the background to prevent garbled display errors.
    # It also allows us to add a stylish border to the centered game area.
    draw_rect(0, 0, w, h, (50, 50, 50), (1.0, 1.0, 1.0))
    draw_rect( -2 + (w - SCREEN_WIDTH) / 2, -2 + (h - SCREEN_HEIGHT) / 2, SCREEN_WIDTH + 4, SCREEN_HEIGHT + 4, (255, 255, 255), (1.0, 1.0, 1.0))

    pygame.display.flip()

    draw_rect(0, 0, w, h, (50, 50, 50), (1.0, 1.0, 1.0))
    draw_rect( -2 + (w - SCREEN_WIDTH) / 2, -2 + (h - SCREEN_HEIGHT) / 2, SCREEN_WIDTH + 4, SCREEN_HEIGHT + 4, (255, 255, 255), (1.0, 1.0, 1.0))
 
    #glViewport( (w - SCREEN_WIDTH), (h - SCREEN_HEIGHT) / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
    #glViewport(50, 50, 480, 360)
    #GL.cset_viewport( (w - SCREEN_WIDTH) / 2, - ((h - SCREEN_HEIGHT) / 2), w, h )
    #GL.cset_viewport(0, 0, int(w / 2), int(h / 2))

    #glScale(0.5, 0.5, 1.0)


# C - Create a scratch pad (frame buffer)
def create_scratch_pad():

    #print "http://www.opengl.org/archives/resources/faq/technical/extensions.htm"
    #print "(Likely, glGenFramebuffersEXT...)"
    #print 5/0

    return GLExt.ccreate_scratch_pad()


# C - Delete a scratch pad
def delete_scratch_pad(buffer_id):

    GLExt.cdelete_scratch_pad(buffer_id)


# C - Activate a scratch pad (create texture of a given size, retrieve texture id)
def activate_scratch_pad(buffer_id, width, height):

    return GLExt.cactivate_scratch_pad(buffer_id, width, height)


# C - Create greyscale shader
def create_greyscale_shader():

    return GLExt.ccreate_greyscale_shader()


# C - Configure greyscale intensity (0 - 100)
def configure_greyscale_intensity(program_id, intensity):

    GLExt.cconfigure_greyscale_intensity(program_id, intensity)


# C - Create directional blur shader
def create_directional_blur_shader():

    return GLExt.ccreate_directional_blur_shader()


# C - Configure directional blur (shader)
def configure_directional_blur(buffer_id, direction, length):

    GLExt.cconfigure_directional_blur(buffer_id, direction, c_float(length))


# C - Delete a shader program
def delete_shader_program(buffer_id):

    GLExt.cdelete_shader_program(buffer_id)


# C - Render to a given scratch pad (frame buffer)
def render_to_scratch_pad(buffer_id, width, height):

    GLExt.crender_to_scratch_pad(buffer_id, width, height)


def set_viewport(x, y, width, height):

    GL.cset_viewport(x, y, width, height)


def pause_clipping():

    GL.cpause_clipping()


def resume_clipping():

    GL.cresume_clipping()


def stencil_enable():

    GL.cstencil_enable()


def stencil_disable():

    GL.cstencil_disable()


def stencil_enable_painting():

    GL.cstencil_enable_painting()


def stencil_enable_erasing():

    GL.cstencil_enable_erasing()


def stencil_enforce_painted_only():

    GL.cstencil_enforce_painted_only()


def stencil_enforce_unpainted_only():

    GL.cstencil_enforce_unpainted_only()


def stencil_clear_region(x, y, w, h):

    GL.cstencil_clear_region(x, y, w, h)


def stencil_clear():

    GL.cstencil_clear()


# Clear all gl buffers
def clear_buffers():

    GL.clear_buffers()


# Enable gl scissor
def scissor_on():

    GL.scissor_on()


# Disable gl scissor
def scissor_off():

    GL.scissor_off()


# Set gl scissor region
def set_scissor(x, y, w, h):

    # Set region
    GL.set_scissor(x, y, w, h)


##############################################################
## OPENGL SPRITE SHEET FUNCTIONS

class GLSpritesheet:

    def __init__(self, path, frameW, frameH, first_pixel_transparent = True, frame_delays = None):

        self.debug = path

        # Load the image onto a surface
        texture_surface = pygame.image.load(path)

        # Image dimensions
        sw = texture_surface.get_width()
        sh = texture_surface.get_height()


        # Store frame details
        self.frameW = frameW
        self.frameH = frameH

        self.frame_delays = frame_delays

        # Calculate frames per row
        self.frames_per_row = sw / float(frameW)


        # Require power-of-2 dimensions.
        textureW = sw
        textureH = sh

        n = 1
        while (textureW > n):
            n *= 2

        textureW = n

        n = 1
        while (textureH > n):
            n *= 2

        textureH = n


        # Require equal texture dimensions
        if (textureW > textureH):
            textureH = textureW

        elif (textureH > textureW):
            textureW = textureH


        # Remember original image width
        self.imageW = float(sw)
        self.imageH = float(sh)


        # Remember texture width
        self.textureW = float(textureW)
        self.textureH = float(textureH)


        final_surface = pygame.Surface((textureW, textureH))
        final_surface.blit(texture_surface, (0, 0))


        # Will we use the top-left pixel for transparency data?
        if (first_pixel_transparent):
            final_surface.set_colorkey(texture_surface.get_at((0, 0)), RLEACCEL)

        # No; let's use a hard-coded purple color instead.
        else:
            final_surface.set_colorkey((255, 0, 255), RLEACCEL)


        # Grab pixel data
        texture_data = pygame.image.tostring(final_surface, "RGBA", 1)

        # Create the GL texture for this spritesheet from that pixel data
        texture_id = GL.create_texture_from_surface(texture_data, textureW, textureH)

        # Keep a handle to that texture id
        self.texture = texture_id

        logn( "gl", "Created texture %s (%s)\n" % (self.texture, self.debug) )


    def __del__(self):
        return


    # Unload spritesheet's texture
    def unload(self):

        #log( "Deleting texture id '%s' for path '%s'" % (self.texture, self.debug) )
        logn( "gl", "Deleted texture %s (%s)\n" % (self.texture, self.debug) )

        # Free the texture
        if (self.texture):

            # Delete it
            delete_texture(self.texture)

            # Safety
            self.texture = None


    # Get original image width
    def get_width(self):

        # Return
        return int(self.imageW)


    # Get original image height
    def get_height(self):

        # Return
        return int(self.imageH)


    def get_texture_id(self):

        return self.texture

    def get_texture_width(self):

        return int(self.textureW)

    def get_texture_height(self):

        return int(self.textureH)

    def get_texture_coordinates(self, index):

        if (index >= 0):

            tstep = self.frameW / self.textureW

            (tx, ty) = (
                (index % self.frames_per_row),
                int(index / self.frames_per_row)
            )

            (tu, tv) = (
                tx * tstep,
                1.0 - (ty * tstep) - tstep
            )

            return (tu, tv, tstep, tstep)


        # Retrieve the entire "surface"
        elif (index == -1):

            return (0, 1.0 - (self.imageH / self.textureH), (self.imageW / self.textureW), (self.imageH / self.textureH))


class GLTextRenderer:

    def __init__(self, p_filename, p_color, p_background_color, p_size=28):

        # Texture ids for each individual letter, hashed by ascii code
        self.all_tiles = {}

        # Width data for each individual letter, hashed by ascii code
        self.all_widths = {}

        # Overall font height (constant across all letters, tallest letter wins)
        self.font_height = 0


        # Load font
        self.font = pygame.font.Font(p_filename, p_size)


        # Remember background color
        self.background = p_background_color

        # Remember text color
        self.foreground = p_color

        # Remember text sizes
        self.font_size = p_size


        cursor = 0

        """
        p_background_color = (255, 0, 0, 0)#(255, 0, 0)
        p_color = (0, 0, 0)
        p_background_color = (255, 255, 255)
        """

        for i in VALID_CHARACTER_CODES:

            self.create_character(i)


    def create_character(self, i):

        try:

            logn( "text error", "%s\n" % i )
            font_surface = self.font.render( unichr(i), 1, self.foreground, self.background).convert_alpha()
            self.all_widths[i] = font_surface.get_width()
            font_surface.set_colorkey(font_surface.get_at((0, 0)), RLEACCEL)
            #font_surface.set_colorkey((255, 0, 0), RLEACCEL)

            w = font_surface.get_width()
            h = font_surface.get_height()

            if (h > self.font_height):
                self.font_height = h

            n = 1
            while (w > n):
                n = n * 2
            w = n

            n = 1
            while (h > n):
                n = n * 2
            h = n

            if (w > h):
                h = w
            elif (h > w):
                w = h

            temp_surface = pygame.Surface((w, h))
            pygame.draw.rect(temp_surface, font_surface.get_at((0, 0)), (0, 0, w, h))
            temp_surface.blit(font_surface, (0, 0))
            temp_surface.set_colorkey(font_surface.get_at((0, 0)))  

            texture_data = pygame.image.tostring(temp_surface, "RGBA", 1)

            # Use module to create a new texture from the surface
            texture_id = GL.create_texture_from_surface(texture_data, w, h)

            # Track texture as well as texture dimensions
            self.all_tiles[i] = (
                texture_id,
                (w, h)
            )

        except:
            log2( "Character error:  %s" % i )
            logn( "text error", "Character error:  %s\n" % i )

            self.all_tiles[i] = (-1, (0, 0))
            self.all_widths[i] = 0


    def process_cache_items(self, window_controller):

        return

        for key in self.cache_items:

            # If we haven't cached the item by this key yet...
            if (not self.cache_items[key].ready):

                self.cache_items[key].perform_caching(self, window_controller)


    # How many lines do we need to render a given string within a certain width?
    def wrap_lines_needed(self, text, max_width = 1000):

        text = text.decode("utf-8")

        lines = self.wordwrap_text(text, 0, 0, (225, 225, 225), max_width = max_width)

        return len(lines)

    def get_last_wrap_line(self, text, max_width = 1000):

        text = text.decode("utf-8")

        lines = self.wordwrap_text(text, 0, 0, (225, 225, 225), max_width = max_width)

        return lines[-1]["text"]

    def wordwrap_text(self, text, x, y, color, max_width = 1000, align = "left", render_range = None):

        # Just in case
        text = text.strip()

        # Track lines we'll need
        lines = []


        # Keep track of which color to use when rendering
        color_stack = [color]

        # Note the points at which colors change
        colors_by_offset = {}

        regex = re.compile("\[color=([a-z]*?)\]")
        match = regex.search(text)

        color_data = []

        while (match):

            (a, b, c) = (
                match.start(),
                match.end(),
                match.groups()[0]
            )

            # Add the newest color to the color stack
            color_stack.append(c)

            # Find the closing tag for this color tag...
            regex2 = re.compile("\[\/color\]")
            match2 = regex2.search(text, b)

            (a2, b2, c2) = (0, 0, None)

            looping = True
            while (looping):

                try:

                    (a2, b2, c2) = (
                        match2.start(),
                        match2.end(),
                        None
                    )

                except:

                    log( text )
                    log( 5/0 )

                # Having found a closing tag, let's count how many open/close color tags exist
                # between b and a2.  They must be equal, or else we haven't found the proper closing tag...
                color_open_tag_count = len( regex.findall(text, b, a2) )
                color_close_tag_count = len( regex2.findall(text, b, a2) )

                # Have we found the proper close tag?
                if (color_open_tag_count == color_close_tag_count):

                    looping = False

                # No?  Then let's keep searching...
                else:

                    match2 = regex2.search(text, b2)

            # At this point we've located the proper close tag.  Let's specify the proper "old" color we'll
            # return to at that point...

            for datum in color_data:

                if (datum["to"] > a):

                    datum["to"] -= (b - a) + (b2 - a2)


            color_data.append({
                "from": a,
                "to": (a2 - (b - a)),
                "color": c
            })


            # Remove all of the markup we found...
            text = text[0:a] + text[b:a2] + text[b2:len(text)]


            # Continue searching for another [color=...] tag...
            match = regex.search(text)


        last_color = color

        for i in range(0, len(color_data)):

            datum = color_data[i]

            colors_by_offset[ datum["from"] ] = datum["color"]

            fallback = color

            for j in range(0, i):

                datum2 = color_data[j]

                if ( (datum2["from"] < datum["from"]) and (datum2["to"] > datum["to"]) ):

                    fallback = datum2["color"]

            colors_by_offset[ datum["to"] ] = fallback


        paragraphs = text.split("\n")

        paragraph_offset = 0


        for paragraph in paragraphs:

            words = paragraph.split(" ")

            # Keep track of the line we're building
            line_width = 0

            # Track our current location with the text string
            last_offset = 0
            offset = 0

            for w in words:

                # Will this word begin a color change?
                regex = re.compile("^\[color=([a-z]*?)\]")
                matches = regex.findall(w)

                word_color = None

                # We'll only have one match (e.g. [color=red])
                if (len(matches) > 0):

                    color_stack.append( matches[0].strip() )
                    colors_by_offset[paragraph_offset + offset] = color_stack[-1]

                w = regex.sub("", w)


                # End of a color?
                regex = re.compile("\[\/color\]$")
                matches = regex.findall(w)

                if (len(matches) > 0):

                    color_stack.pop()
                    colors_by_offset[paragraph_offset + offset + len(w)] = color_stack[-1]

                w = regex.sub("", w)


                w = w + " "

                # Calculate word width
                word_width = self.size(w)

                # Will we have room on the current line?
                if (line_width + word_width <= max_width):
                    line_width += word_width

                    offset += len(w)

                # Nope; we need to mark the current offset position as this line's boundary
                # and move to a new line...
                else:
                    lines.append({
                        "begin": paragraph_offset + last_offset,
                        "end": paragraph_offset + offset,
                        "width-used": line_width
                    })

                    # Track last offset point
                    last_offset = offset

                    line_width = word_width

                    # Continue through the text string...
                    offset += len(w) + 0 # Account for whitespace



            # Always add in the last line that didn't reach the limit...
            lines.append({
                "begin": paragraph_offset + last_offset,
                "end": paragraph_offset + len(paragraph),
                "width-used": line_width,
                "x": 0,
                "y": 0,
                "text": "",
                "colors-by-offset": None
            })

            paragraph_offset += len(paragraph) + 1


        # Which lines will we render?  By default, render all...
        valid_range = range(0, len(lines))

        # If we specified a certain range, though...
        if (render_range):

            valid_range = render_range


        # Render all lines...
        for i in range(0, len(lines)):

            if (i in valid_range):

                (rx, ry) = (x, y + ( (i - valid_range[0]) * self.font_height))

                if (align == "center"):
                    rx -= int(lines[i]["width-used"] / 2)

                elif (align == "right"):
                    rx -= lines[i]["width-used"]

                s = text[ lines[i]["begin"] : lines[i]["end"] ]

                regex = re.compile("\[color=([a-z]*?)\]")
                s = regex.sub("", s)

                regex = re.compile("\[\/color\]")
                s = regex.sub("", s)


                (a, b) = (
                    lines[i]["begin"],
                    lines[i]["end"]
                )

                # Calculate which color offsets pertain (and by what relative length) to this substring...
                substring_colors_by_offset = {}


                # Any line other than the first line should resume the color the previous line ended on...
                if (i > 0):

                    # Default to primary color
                    substring_colors_by_offset[0] = color

                    # Now loop through and change colors as necessary...
                    offsets = colors_by_offset.keys()
                    offsets.sort()

                    for offset in offsets:

                        offset = int(offset)

                        if (offset < a):

                            substring_colors_by_offset[0] = colors_by_offset[offset]


                for offset in colors_by_offset:

                    offset = int(offset)

                    if (offset >= a and offset < b):
                        substring_colors_by_offset[offset - a] = colors_by_offset[offset]

                lines[i]["text"] = s
                lines[i]["colors-by-offset"] = substring_colors_by_offset

                lines[i]["x"] = rx
                lines[i]["y"] = ry

        return lines


    def render_with_wrap(self, text, x, y, color = (255, 255, 255), max_width = 1000, align = "left", letter_fade_percentages = [], render_range = None, cache_key = None, color_classes = {}, color2 = None):

        # Before we begin, let's see if we want to try to cache this render task...
        #if (cache_key):
        #    # Add / update this cache item...
        #    self.cache_items[cache_key] = GLTextRendererCacheItem(text, color, color2, max_width, align, color_classes)
        #    # Run the cache job (using the common scratch pad, ultimately)
        #    self.cache_items[cache_key].perform_caching(self, window_controller)

        text = text.decode("utf-8")

        lines = self.wordwrap_text(text, x, y, color, max_width, align, render_range)

        for line in lines:

            self.render(line["text"], line["x"], line["y"], color, -1, None, False, letter_fade_percentages[ line["begin"] : line["end"] ], colors_by_offset = line["colors-by-offset"], color_classes = color_classes, p_color2 = color2, encoding = "utf-8")


        return (self.font_height * len(lines))


    # Render a string of text to the active framebuffer using word wrap,
    # then return a new texture that contains the resulting block of text.
    def render_and_clip_with_wrap(self, text, color = (255, 255, 255), max_width = 1000, align = "left", letter_fade_percentages = [], render_range = None, color_classes = {}, color2 = None, window_controller = None):

        # Clear with transparent color.(hard-coded color)
        draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (255, 0, 255, 1))

        # Default texture dimensions
        w = max_width
        h = self.render_with_wrap(text, 0, 0, set_alpha_for_rgb(1.0, (color)), max_width, align, letter_fade_percentages, render_range, color_classes = color_classes, color2 = color2)

        # If we fit it all on one line, then the texture only needs to be as wide
        # as the string we rendered.
        if (h == self.font_height):

            # Calculate width of the one-line string
            w = self.size(text, max_width)

        # If we had to wrap lines, then clearly we used (more or less) the entire "max width."
        # Thus, our texture will need to be at least that wide.
        else:
            w = max_width

        # Find a power-of-2 texture size to fit the data...
        s = 2

        while (s < max(w, h)):

            s *= 2

        # Clip from the common scratchpad
        (texture_id, s, s) = clip_backbuffer(0, 0, w, h, window_controller)

        # Make sure we have proper transparency set on the new texture
        GL.set_color_key_on_texture(texture_id, s, s, list3_to_c_double_array( (255, 0, 255) ))

        # Return the "cached" text block (and dimension).
        return (texture_id, s, s)


    def render(self, p_text, p_x, p_y, p_color=(255,255,255), p_max_width=-1, p_angle = None, auto_wrap = False, letter_fade_percentages = [], colors_by_offset = {}, p_color2 = None, p_align = "left", scale = 1, color_classes = {}, encoding = None):

        if (encoding == None):
            p_text = p_text.decode("utf-8")

        width_used = 0 # We'll keep track of how much width we've used to render
                       # the text in case we have a width limit.

        color_stack = [ rgb_to_glcolor(p_color) ]

        # Gradient steps
        tstepRGB = None

        tw = self.size(p_text)

        if (p_align == "right"):
            p_x -= tw

        elif (p_align == "center"):
            p_x -= int(tw / 2)


        if (p_color2 and tw > 0):

            p_color2 = rgb_to_glcolor(p_color2)

            tstepRGB = (
                (p_color2[0] - color_stack[-1][0]) / float(tw),
                (p_color2[1] - color_stack[-1][1]) / float(tw),
                (p_color2[2] - color_stack[-1][2]) / float(tw),
                (p_color2[3] - color_stack[-1][3]) / float(tw)
            )


        (rx, ry) = (p_x, p_y)

        i = 0
        while (i < len(p_text)):

            # Check for coloring
            if (i in colors_by_offset):

                color_name = colors_by_offset[i]

                # Default to original color
                new_color = color_stack[0]

                if (color_name in color_classes):
                    new_color = rgb_to_glcolor( set_alpha_for_rgb( color_stack[0][3], color_classes[color_name] ) )

                color_stack.append( new_color )

            x = 0 + int(ord(p_text[i]))

            if ( not (x in self.all_widths) ):
                if (x != 32):
                    logn( "text error", "%s" % x )
                    logn( "text error", " (not in all widths)\n" )

            #if (x > 32 and x < 166):
            if ( x in self.all_widths ):
                width_used += self.all_widths[x]#x - 33]

                if (p_max_width >= 0 and width_used > p_max_width):

                    # This function no longer supports automatic word-wrap.  (glTranslate should not be called directly here, anyway.)
                    # Use render_witH_wrap instead.

                    # Abandon while loop
                    break

                visible = True

                # Some foreign characters might fail
                if ( self.all_tiles[x][0] == -1 ):
                    visible = False

                if (visible):

                    info = self.all_tiles[x]

                    if (p_color2):

                        if (scale > 1):

                            (u, v) = (
                                int(info[1][0] * scale),
                                int(info[1][1] * scale)
                            )

                            (sx, sy) = (
                                -int( (u - info[1][0]) / 2),
                                -int( (v - info[1][1]) / 2)
                            )

                            draw_texture_with_gradient(info[0], sx + rx, sy + ry, u, v, increment_glcolor_by_n_gradient_steps(color_stack[-1], width_used, tstepRGB), increment_glcolor_by_n_gradient_steps(p_color2, width_used, tstepRGB))

                        else:

                            (glcolor1, glcolor2) = (
                                increment_glcolor_by_n_gradient_steps(color_stack[-1], width_used - self.all_widths[x], tstepRGB),
                                increment_glcolor_by_n_gradient_steps(color_stack[-1], width_used, tstepRGB)
                            )

                            draw_texture_with_gradient(info[0], rx, ry, info[1][0], info[1][1], glcolor1, glcolor2)

                    else:

                        if (len(letter_fade_percentages) > i):

                            draw_texture(info[0], rx, ry, info[1][0], info[1][1], multiply_glcolor_alpha_by_coefficient(color_stack[-1], letter_fade_percentages[i]) )

                        else:

                            draw_texture(info[0], rx, ry, info[1][0], info[1][1], color_stack[-1])

                if (scale == 1):
                    rx += self.all_widths[x]

                else:
                    rx += int(self.all_widths[x] * scale)

            # Space (" " == ASCII value of 32)
            elif (x == 32):

                rx += 5
                width_used += 5

            # Try to create a foreign character
            else:
                self.create_character(x)

            i += 1


    def render_as_html(self, p_text, p_x, p_y, p_color=(0, 0, 0), p_max_width=-1, p_angle = None, auto_wrap = False, letter_fade_percentages = [], colors_by_offset = {}, p_color2 = None, p_align = "left", scale = 1, color_classes = {}, encoding = None):

        html = ""

        if (encoding == None):
            p_text = p_text.decode("utf-8")

        color_stack = [ rgb_to_hex(p_color) ]

        (rx, ry) = (p_x, p_y)

        span_count = 0

        i = 0
        while (i < len(p_text)):

            # Check for coloring
            if (i in colors_by_offset):

                color_name = colors_by_offset[i]

                # Default to original color
                new_color = color_stack[0]

                if (color_name in color_classes):
                    new_color = rgb_to_hex( color_classes[color_name] )

                color_stack.append( new_color )

                html += "<span style = 'color: %s'>" % new_color
                span_count += 1

            html += "%s" % p_text[i]

            i += 1


        for i in range(0, span_count):
            html += "</span>"

        return html


    # Calculate the width required to render a string of text.  Currently returns with "current" width
    # if "p_max_width" is exceeded (with overrun?).
    def size(self, p_text, p_max_width=-1):

        total_width = 0

        # Replace markup
        regex = re.compile("\[color=[a-z]*?\]")
        p_text = regex.sub("", p_text)

        regex = re.compile("\[\/color\]")
        p_text = regex.sub("", p_text)

        for i in range(0, len(p_text)):
            x = 0 + int(ord(p_text[i]))
            #if (x > 32 and x < 166):
            if ( x in self.all_widths ):
                #print p_text[i], p_text, x
                #print ( p_text[i], "width = %s" % self.all_widths[x] )
                total_width += self.all_widths[x]

                if (p_max_width >= 0 and total_width >= p_max_width):
                    return total_width

            elif (x == 32):
                total_width += 5

                if (p_max_width >= 0 and total_width >= p_max_width):
                    return total_width

        return total_width

##############################################################
## OPENGL MISC. FUNCTIONS

def delete_texture(texture_id):

    GL.cdelete_texture(texture_id)


def copy_texture_to_texture(texture_id1, texture_id2, w, h):

    GL.ccopy_texture_to_texture(texture_id1, texture_id2, w, h)


def clone_texture(texture_id1, w, h):

    return GL.cclone_texture(texture_id1, w, h)


def replace_color_on_texture(texture_id, w, h, color1, color2):

    GL.creplace_color_on_texture(
        texture_id,
        w,
        h,
        list3_to_c_double_array(color1),
        list3_to_c_double_array(color2)
    )


def set_visible_region_on_texture(texture_id, w, h, r):

    cparam = list4_to_c_int_array( flip_rect(r, w, h) )

    GL.cset_visible_region_on_texture(texture_id, w, h, cparam)


def draw_line(x1, y1, x2, y2, p_color, p_size = 1):

    if (p_color):

        GL.cdraw_line(
            x1,
            y1,
            x2,
            y2,
            list4_to_c_double_array( rgb_to_glcolor(p_color) ),
            p_size
        )


def draw_rect(x, y, width, height, p_color, p_current_color = (255, 255, 255), test = 0):

    if (p_color):

        try:

            if (test == 0):

                # call module
                GL.cdraw_rect(
                    int(x),
                    int(y),
                    width,
                    height,
                    list4_to_c_double_array( rgb_to_glcolor(p_color) )
                )

            else:

                # call module
                GL.cdraw_rect2(
                    int(x),
                    int(y),
                    width,
                    height,
                    list4_to_c_double_array( rgb_to_glcolor(p_color) )
                )
        except:
            log( "p_color = ", p_color )
            log( "rgb_to = ", rgb_to_glcolor(p_color) )
            log( "y = ", y )
            log( 5/0 )


def draw_rect_frame(x, y, width, height, p_color, p_frame_size, p_current_color = (255, 255, 255)):

    if (p_color):

        GL.cdraw_rect_frame(
            x,
            y,
            width,
            height,
            list4_to_c_double_array( rgb_to_glcolor(p_color) ),
            p_frame_size
        )


def draw_rect_with_horizontal_gradient(x, y, width, height, color1, color2):

    (cparam1, cparam2) = (
        list4_to_c_double_array( rgb_to_glcolor(color1) ),
        list4_to_c_double_array( rgb_to_glcolor(color2) )
    )

    GL.cdraw_rect_with_horizontal_gradient(
        int(x),
        int(y),
        width,
        height,
        cparam1,
        cparam2
    )


def draw_rect_with_vertical_gradient(x, y, width, height, color1, color2):

    (cparam1, cparam2) = (
        list4_to_c_double_array( rgb_to_glcolor(color1) ),
        list4_to_c_double_array( rgb_to_glcolor(color2) )
    )

    GL.cdraw_rect_with_vertical_gradient(
        int(x),
        int(y),
        width,
        height,
        cparam1,
        cparam2
    )



def draw_circle(cx, cy, radius, background = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

    # Does this circle need a border?
    if (border):

        GL.cdraw_circle_with_border(
            cx,
            cy,
            radius,
            list4_to_c_double_array( rgb_to_glcolor(background) ),
            accuracy,
            start,
            end,
            list4_to_c_double_array( rgb_to_glcolor(border) ),
            border_size
        )

    # Surely it has at least a background color...
    elif (background):

        GL.cdraw_circle(
            cx,
            cy,
            radius,
            list4_to_c_double_array( rgb_to_glcolor(background) ),
            accuracy,
            start,
            end
        )


def draw_circle_with_gradient(cx, cy, radius, background1 = None, background2 = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

    # Does this circle need a border?
    if (border):

        GL.cdraw_circle_with_border(
            cx,
            cy,
            radius,
            list4_to_c_double_array( rgb_to_glcolor(background) ),
            accuracy,
            start,
            end,
            list4_to_c_double_array( rgb_to_glcolor(border) ),
            border_size
        )

    # Surely it has at least a background color...
    elif (background1 and background2):

        GL.cdraw_circle_with_gradient(
            cx,
            cy,


            radius,
            list4_to_c_double_array( rgb_to_glcolor(background1) ),
            list4_to_c_double_array( rgb_to_glcolor(background2) ),
            accuracy,
            start,
            end
        )


def draw_circle_with_radial_gradient(cx, cy, radius, background1 = None, background2 = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

    GL.cdraw_circle_with_radial_gradient(
        cx,
        cy,
        radius,
        list4_to_c_double_array( rgb_to_glcolor(background1) ),
        list4_to_c_double_array( rgb_to_glcolor(background2) ),
        accuracy,
        start,
        end
    )


def draw_exclusive_circle_with_radial_gradient(cx, cy, radius, background1 = None, background2 = None, border = None, accuracy = 5, start = 0, end = 360, border_size = 1):

    GL.cdraw_exclusive_circle_with_radial_gradient(
        cx,
        cy,
        radius,
        list4_to_c_double_array( rgb_to_glcolor(background1) ),
        list4_to_c_double_array( rgb_to_glcolor(background2) ),
        accuracy,
        start,
        end
    )


def draw_radial_arc(cx, cy, start, end, radius, thickness, background, border, accuracy = 20):

    GL.cdraw_radial_arc(
        cx,
        cy,
        start,
        end,
        radius,
        thickness,#list4_to_c_double_array( rgb_to_glcolor(background) ),
        list4_to_c_double_array( rgb_to_glcolor(border) ),
        accuracy
    )


def draw_radial_arc_with_gradient(cx, cy, start, end, radius, thickness, background1, background2, border, accuracy = 20):

    GL.cdraw_radial_arc_with_gradient(
        cx,
        cy,
        start,
        end,
        radius,
        thickness,
        list4_to_c_double_array( rgb_to_glcolor(background1) ),
        list4_to_c_double_array( rgb_to_glcolor(background2) ),
        list4_to_c_double_array( rgb_to_glcolor(border) ),
        accuracy
    )


def draw_clock_rect(x, y, w, h, background = None, border = None, border_size = 1, degrees = 360):

    # Right now I don't support drawing any border, maybe later...
    if (background):

        GL.cdraw_clock_rect(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(background) ),
            degrees
        )


def draw_rounded_rect(x, y, w, h, background = None, border = None, border_size = 1, radius = 5, shadow = None, shadow_size = 1):

    GL.cdraw_rounded_rect(
        x,
        y,
        w,
        h,
        list4_to_c_double_array( rgb_to_glcolor(background) ),
        radius
    )

    if (border):

        GL.cdraw_rounded_rect_frame(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(border) ),
            border_size,
            radius
        )

        if (shadow):

            GL.cdraw_rounded_rect_frame(
                x + border_size,
                y + border_size,
                w - (2 * border_size),
                h - (2 * border_size),
                list4_to_c_double_array( rgb_to_glcolor(shadow) ),
                shadow_size,
                radius
            )


def draw_rounded_rect_frame(x, y, w, h, color, border_size = 1, radius = 5, shadow = None, shadow_size = 1):

    GL.cdraw_rounded_rect_frame(
        x,
        y,
        w,
        h,
        list4_to_c_double_array( rgb_to_glcolor(color) ),
        border_size + shadow_size,
        radius
    )

    if (shadow):

        GL.cdraw_rounded_rect_frame(
            x + border_size,
            y + border_size,
            w - (2 * border_size),
            h - (2 * border_size),
            list4_to_c_double_array( rgb_to_glcolor(shadow) ),
            shadow_size,
            radius
        )


def draw_rounded_rect_with_gradient(x, y, w, h, background1 = None, background2 = None, border = None, border_size = 1, radius = 5, shadow = None, shadow_size = 1, gradient_direction = DIR_RIGHT):

    if (gradient_direction == DIR_RIGHT):

        GL.cdraw_rounded_rect_with_horizontal_gradient(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(background1) ),
            list4_to_c_double_array( rgb_to_glcolor(background2) ),
            radius
        )

    elif (gradient_direction == DIR_DOWN):

        GL.cdraw_rounded_rect_with_vertical_gradient(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(background1) ),
            list4_to_c_double_array( rgb_to_glcolor(background2) ),
            radius
        )


    if (border):

        GL.cdraw_rounded_rect_frame(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(border) ),
            border_size + shadow_size,
            radius
        )

        if (shadow):

            GL.cdraw_rounded_rect_frame(
                x + border_size,
                y + border_size,
                w - (2 * border_size),
                h - (2 * border_size),
                list4_to_c_double_array( rgb_to_glcolor(shadow) ),
                shadow_size,
                radius
            )

            #draw_rounded_rect_with_gradient(x + shadow_size, y + shadow_size, w - (2 * shadow_size), h - (2 * shadow_size), background = background, border = shadow, border_size = shadow_size, radius = radius, shadow = None)


def draw_rect_with_gradient(x, y, w, h, background1 = None, background2 = None, gradient_direction = DIR_RIGHT):

    if (gradient_direction == DIR_RIGHT):

        GL.cdraw_rect_with_horizontal_gradient(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(background1) ),
            list4_to_c_double_array( rgb_to_glcolor(background2) )
        )

    elif (gradient_direction == DIR_DOWN):

        GL.cdraw_rect_with_vertical_gradient(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(background1) ),
            list4_to_c_double_array( rgb_to_glcolor(background2) )
        )

    elif (gradient_direction == DIR_UP):

        GL.cdraw_rect_with_vertical_gradient(
            x,
            y,
            w,
            h,
            list4_to_c_double_array( rgb_to_glcolor(background2) ),
            list4_to_c_double_array( rgb_to_glcolor(background1) )
        )


# This function is a little bit messy.  It calls
# glStart / glEnd outside of all of the logic,
# and returns one or more quads (skipping empty
# tiles yields more quads...).
def draw_textured_row(x, y, tilesheet_sprite, tile_values = [], gl_color = None, min_x = 0, max_x = SCREEN_WIDTH, min_y = 0, max_y = SCREEN_HEIGHT, scale = 1.0):#window_x = 0, window_y = 0):

    # Don't render off-screen rows
    if ( ( (y + TILE_HEIGHT) < min_y ) or (y >= max_y) ):
        return


    # Position
    GL.cplace_gl_cursor(min_x + x, min_y + y, 0)

    # Texture
    GL.cset_texture(tilesheet_sprite.texture)


    # Are we actively rendering at the moment?
    rendering = False

    # The offset at which we'll begin rendering.  No point in checking tiles in the row
    # that aren't even on the screen...
    start = 0

    # We're starting offscreen.  Let's skip any offscreen tile...
    if (x < 0):

        start = abs( int( (x - 0) / int(scale * TILE_WIDTH)) ) - 1


    # Check rendering color
    color = (1.0, 1.0, 1.0, 1.0)

    if (gl_color):

        if (len(gl_color) == 3):
            color = (gl_color[0], gl_color[1], gl_color[2], 1.0)

        else:
            color = (gl_color[0], gl_color[1], gl_color[2], gl_color[3])

    # Convert render color to a c-style array
    cparam1 = list4_to_c_double_array( (color[0], color[1], color[2], color[3]) )

    # Set color
    GL.cgl_color(cparam1)

    # Render valid tiles
    for i in range(start, len(tile_values)):

        # Is there a tile at this row position to render?
        if (tile_values[i] > 0):

            # Convert texture coordinates to a c style array
            cparam2 = list4_to_c_double_array( tilesheet_sprite.get_texture_coordinates(tile_values[i]) )

            # Where to render the current tile in the currently active quad?
            (px, py) = (
                (i * int(scale * TILE_WIDTH)),
                0
            )

            # If we've gone out of bounds to the right, then we're done rendering this row...
            if (min_x + x + px >= max_x):

                # If we were still rendering, end the quad and exit the function (we're done!)
                if (rendering):

                    # Just for safety
                    rendering = False

                    # End rendering
                    GL.cgl_end()

                # We've run off the screen already; we can't possibly render more...
                return

            # If this tile fits on the screen, then make sure we're actively rendering...
            elif (not rendering):

                # Flag true
                rendering = True

                # Begin rendering a quad
                GL.cgl_begin_quad()#(GL_QUAD_STRIP)

            # Render the tile with the appropriate texture coordinate data and all that, "in place"...
            GL.cdraw_texture_in_place_with_tex_coords(tilesheet_sprite.texture, px, py, int(scale * TILE_WIDTH), int(scale * TILE_HEIGHT), cparam2)

        # Don't render empty tiles (there's nothing to render).  Instead, just end the current quad... maybe we'll
        # have more tiles to render farther on down the row...
        else:

            if (rendering):

                # Flag off
                rendering = False

                # End rendering
                GL.cgl_end()


    # Now that we've reached the end of the row, are we still busy rendering?
    # If so, we need to place one final call to end rendering for the active quad...
    if (rendering):

        GL.cgl_end()


    # Just to be sure...
    GL.cgl_color( list4_to_c_double_array( (1, 1, 1, 1) ) )

    return



def draw_particle(x, y, index_x, index_y, degrees, tile, tilesheet_sprite, color):

    # Get tex coord data
    (tu, tv, tstepX, tstepY) = tilesheet_sprite.get_texture_coordinates(tile)
    tstep_offset = (tstepX / 3.0)

    # Adjust for the particle's x/y index position
    tu += (index_x * tstep_offset)

    tv += ( (2 - index_y) * tstep_offset)


    # Create c-style array for tex coord data
    cparam = list4_to_c_double_array( (tu, tv, tstep_offset, tstep_offset) )

    # Particle color
    cparam2 = list4_to_c_double_array( rgb_to_glcolor(color) )


    # Call c module function
    GL.cdraw_particle(x, y, PARTICLE_WIDTH, PARTICLE_HEIGHT, index_x, index_y, c_double(degrees), tile, tilesheet_sprite.texture, cparam, cparam2)



def debug_fill_pattern(texture_id):

    log( "texture_id:  ", texture_id )
    GL.debug_fill_pattern(texture_id, 128, 128, list3_to_c_double_array((255, 0, 255)))

def draw_fill_pattern(x, y, tile, tilesheet_sprite, frame, fill_sprite, gl_color = None):

    # Default to full color
    color = (1.0, 1.0, 1.0, 1.0)

    # If we specified another color...
    if (gl_color):

        if (len(gl_color) == 3):
            color = (gl_color[0], gl_color[1], gl_color[2], 1.0)

        else:
            color = (gl_color[0], gl_color[1], gl_color[2], gl_color[3])


    # c array for tilesheet tex coords
    cparam1 = list4_to_c_double_array( tilesheet_sprite.get_texture_coordinates(tile) )

    # c array for fill sprite text coords
    cparam2 = list4_to_c_double_array( fill_sprite.get_texture_coordinates(frame) )

    # c array for color data
    cparam3 = list4_to_c_double_array( color )


    # Call module
    GL.cdraw_fill_pattern(x, y, tile, TILE_WIDTH, TILE_HEIGHT, tilesheet_sprite.texture, cparam1, frame, fill_sprite.get_texture_id(), cparam2, cparam3)


def draw_texture(texture, x, y, w, h, color = (1, 1, 1, 1)):

    c_double_array = c_double * 4

    GL.cdraw_texture(
        texture,
        x,
        y,
        w,
        h,
        list4_to_c_double_array( (color[0], color[1], color[2], color[3]) )
    )


def draw_texture_with_gradient(texture, x, y, w, h, color1 = (1, 1, 1, 1), color2 = (1, 1, 1, 1)):

    c_double_array = c_double * 4

    GL.cdraw_texture_with_gradient(
        texture,
        x,
        y,
        w,
        h,
        list4_to_c_double_array( (color1[0], color1[1], color1[2], color1[3]) ),
        list4_to_c_double_array( (color2[0], color2[1], color2[2], color2[3]) )
    )


def draw_texture_with_texture_coords(texture_id, texture_coords, x, y, w, h, gl_color = (1, 1, 1, 1), degrees = 0):

    # Generate c double array
    cparam = list4_to_c_double_array(gl_color)

    # Get specified texture coordinates
    (tu, tv, tstepX, tstepY) = texture_coords

    # Render the texture
    GL.cdraw_texture_with_tex_coords(texture_id, x, y, w, h, c_double(texture_coords[0]), c_double(texture_coords[1]), c_double(texture_coords[2]), c_double(texture_coords[3]), cparam)


def draw_rotated_texture_with_texture_coords(degrees, texture_id, texture_coords, x, y, w, h, gl_color = (1, 1, 1, 1)):

    # Generate c double array
    cparam = list4_to_c_double_array(gl_color)

    # Get specified texture coordinates
    (tu, tv, tstepX, tstepY) = texture_coords

    # Render the texture
    GL.cdraw_rotated_texture_with_tex_coords(c_double(degrees), texture_id, x, y, w, h, c_double(texture_coords[0]), c_double(texture_coords[1]), c_double(texture_coords[2]), c_double(texture_coords[3]), cparam)


def draw_sprite(x, y, w, h, sprite, frame = 0, gl_color = None, degrees = 0, visibility_region = None, hflip = False, vflip = False, working_texture = None, scale = 1.0):

    if (w == 0 or h == 0):

        return

    elif (visibility_region):

        if ( ( (y + h) < 0 ) or (y >= SCREEN_HEIGHT) ):
            return

        elif ( ( (x + w) < 0 ) or (x >= SCREEN_WIDTH) ):
            return


    # Default to full color
    color = (1.0, 1.0, 1.0, 1.0)

    # If we specified another color...
    if (gl_color):

        if (len(gl_color) == 3):
            color = (gl_color[0], gl_color[1], gl_color[2], 1.0)

        else:
            color = (gl_color[0], gl_color[1], gl_color[2], gl_color[3])


    # Create a c-style array, double[]
    c_double_array = c_double * 4
    cparam = c_double_array(color[0], color[1], color[2], color[3])


    # Get texture coordinates for the specified frame
    (tu, tv, tstepX, tstepY) = sprite.get_texture_coordinates(frame)

    # frame -1 returns texture coordinates for the entire spritesheet (useful for rendering a tilesheet in an editor, for instance)
    if (frame == -1):

        (tu, tv, tstepX, tstepY) = sprite.get_texture_coordinates(-1)


    # Mirror the texture coordinates along the X axis if specified
    if (hflip):

        tu += tstepX
        tstepX *= -1


    # Use the sprite's default texture, or use an overwrite?
    # Default first...
    texture_id = sprite.get_texture_id()

    # Check for an overwrite...
    if (working_texture):

        texture_id = working_texture


    # Render the texture
    GL.cdraw_rotated_texture_with_tex_coords(c_double(degrees), texture_id, visibility_region[0] + x, visibility_region[1] + y, int(scale * w), int(scale * h), c_double(tu), c_double(tv), c_double(tstepX), c_double(tstepY), cparam)


def draw_triangle(x, y, w, h, background_color, border_color, orientation = DIR_UP):

    if (border_color != None):

        border_color = rgb_to_glcolor(border_color)
        background_color = rgb_to_glcolor(background_color)

        # C-style arrays
        c_double_array1 = c_double * 4
        cparam1 = c_double_array1(border_color[0], border_color[1], border_color[2], border_color[3])

        c_double_array2 = c_double * 4
        cparam2 = c_double_array2(background_color[0], background_color[1], background_color[2], background_color[3])

        # Call module
        GL.cdraw_triangle_with_border(x, y, w, h, cparam1, cparam2, orientation)

    else:

        background_color = rgb_to_glcolor(background_color)

        # C-style array
        c_double_array2 = c_double * 4
        cparam2 = c_double_array2(background_color[0], background_color[1], background_color[2], background_color[3])

        # Call module
        GL.cdraw_triangle_without_border(x, y, w, h, cparam2, orientation)


def apply_greyscale_effect_to_texture(texture_id, w, h, percent):

    GL.capply_greyscale_effect_to_texture(texture_id, w, h, c_double(percent))


def apply_greyscale_effect_to_screen(x, y, w, h, percent):

    GL.capply_greyscale_effect_to_screen(x, y, w, h, c_double(percent))


def apply_radial_greyscale_effect_to_screen(x, y, w, h, percent, angle):

    GL.capply_radial_greyscale_effect_to_screen(x, y, w, h, c_double(percent), angle)


def clip_backbuffer(x, y, w, h, window_controller):

    # Find a power-of-2 texture size to fit the data...
    s = 2

    while (s < max(w, h)):

        s *= 2


    # Call module to grab appropriate region...
    texture_id = GL.cclip_backbuffer(x, (window_controller.current_render_height - s), s)

    # Return the new texture with dimensions...
    return (texture_id, s, s)




def create_shader1():

    return GLExt.ccreate_shader1()

def use_program(program):

    GLExt.cuse_program(program)




def flip_rect(r, w, h):

    return (r[0], h - r[1] - r[3], r[2], r[3])

def list3_to_c_double_array(l):

    # Createa c-style array (e.g. double arr[])
    c_double_array = c_double * 3

    # Populate and return arrac style array
    return c_double_array(l[0], l[1], l[2])

def list4_to_c_double_array(l):

    # Createa c-style array (e.g. double arr[])
    c_double_array = c_double * 4

    # Populate and return arrac style array
    return c_double_array(l[0], l[1], l[2], l[3])

def list4_to_c_int_array(l):

    # Createa c-style array (e.g. double arr[])
    c_int_array = c_int * 4

    # Populate and return arrac style array
    return c_int_array(l[0], l[1], l[2], l[3])
