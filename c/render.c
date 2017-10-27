#include <GL/gl.h>
#include <GL/glu.h>

//nonfunctional until pystring and pygame get their c/c++ interpreter reworked 
/* #include <pystring.h>
#include <pygame1.h> */

#include <string.h>
#include <stdlib.h>
#include <math.h>

const int SCREEN_WIDTH = 640;
const int SCREEN_HEIGHT = 480;

const int DIR_UP = 0;
const int DIR_RIGHT = 1;
const int DIR_DOWN = 2;
const int DIR_LEFT = 3;


// to compile:
//    gcc -O2 -o gltest1dll.dll -shared  gltest1.c


// Convenience function
double degrees_to_radians(double degrees)
{
    return (degrees * M_PI / 180.0);
}


// Convenience function
int radians_to_degrees(double radians)
{
    return ((radians / (2 * M_PI)) * 360);
}


// Set up opengl
void csetup_opengl(int w, int h)
{
    // Basic settings
    glClearColor(0.0, 0.0, 0.0, 1.0);
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
 
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();

    // this puts us in quadrant 1, rather than quadrant 4
    gluOrtho2D(0, w, h, 0);
    glMatrixMode(GL_MODELVIEW);

    // set up texturing
    glEnable(GL_TEXTURE_2D);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
}


// Set viewport
void cset_viewport(int x, int y, int w, int h)
{
    glViewport(x, y, w, h);
}


// Create texture from image data (e.g. pygame surface)
int create_texture_from_surface(void *texture_data, int w, int h)
{
    // Generate a texture id
    int texture_id = 0;
    glGenTextures(1, &texture_id);

    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data);

    // Return texture id
    return texture_id;
}


// Update a texture from image data
void update_texture_from_surface(int texture_id, void *texture_data, int w, int h)
{
    // Bind the specified texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data);
}


// Delete a texture
void cdelete_texture(int texture_id)
{
    glDeleteTextures(1, &texture_id);
}


// Get raw texture data
GLubyte* get_raw_texture_data(int texture_id, int w, int h)
{
    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Get the texture data...
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);
    //GLubyte buffer[w * h * 4];
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // Return raw data
    return buffer;
}

// Release that raw texture data (allocated memory)
void release_raw_texture_data(GLubyte *buffer)
{
    free(buffer);
}


void get_reverse_buffer(GLubyte *buffer, GLubyte *dest, int w, int h)
{
    int u = 0, v = 0;
    for (v = 0; v < h; v += 1)
    {
        for (u = 0; u < w; u += 1)
        {
            int pos1 = ((h - v - 1) * w * 4) + (u * 4);
            int pos2 = (v * w * 4) + (u * 4);

            dest[pos2] = buffer[pos1];
            dest[pos2 + 1] = buffer[pos1 + 1];
            dest[pos2 + 2] = buffer[pos1 + 2];
            dest[pos2 + 3] = buffer[pos1 + 3];
        }
    }
}

void debug_fill_pattern(int texture_id, int w, int h, double color_key[])
{
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);
    GLubyte *buffer_flipped = (GLubyte *) malloc(w * h * 4);

    //int *history = (int *) malloc(24 * 24 * sizeof(int));

    int history[24][24];

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer_flipped);

    get_reverse_buffer(buffer_flipped, buffer, w, h);

    int f = 0, u = 0, v = 0;

    for (v = 0; v < 24; v += 1)
    {
        for (u = 0; u < 24; u += 1)
        {
            history[v][u] = 0;
        }
    }

    for (f = 0; f < 12; f += 1)
    {
        int row = (f / 4);
        int col = (f % 4);

        for (v = 0; v < 24; v += 1)
        {
            for (u = 0; u < 24; u += 1)
            {
                int pos = (row * w * 4 * 24) + (v * w * 4) + (col * 24 * 4) + (u * 4);

                double pixel_rgb[3] = {
                    buffer[pos],
                    buffer[pos + 1],
                    buffer[pos + 2]
                };

                if ( (color_key[0] == pixel_rgb[0]) && (color_key[1] == pixel_rgb[1]) && (color_key[2] == pixel_rgb[2]) )
                {
                    //if (history[(v * 24 * sizeof(int)) + (u * sizeof(int))] == 1)
                    if (history[v][u] != 1)
                    {
                        buffer[pos] = 255;
                        buffer[pos + 1] = 0;
                        buffer[pos + 2] = 0;
                        buffer[pos + 3] = 255;

                        history[v][u] = 1;
                    }

                    else if (1)
                    {
                        buffer[pos] = 0;
                        buffer[pos + 1] = 255;
                        buffer[pos + 2] = 0;
                        buffer[pos + 3] = 255;
                    }

                    //history[(v * 24 * sizeof(int)) + (u * sizeof(int))] = 1;

                    // Then we're going to set that to 0 alpha in the texture data buffer we grabbed (0 being fully transparent)
                    //buffer[pos + 3] = 0;
                }

                else if (0)
                {
                    buffer[pos] = 255;
                    buffer[pos + 1] = 255;
                    buffer[pos + 2] = 0;
                }
            }
        }
    }

    get_reverse_buffer(buffer, buffer_flipped, w, h);

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer_flipped);

    //free(history);

    // We're done with the buffer
    free(buffer);
    free(buffer_flipped);
}


// Specify a color as transparent on a texture
void set_color_key_on_texture(int texture_id, int w, int h, double color_key[])
{
    // Allocate the memory we'll need
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Get the data from that texture
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // Loop through each pixel in the texture data buffer (4 bytes apiece, rgb and alpha)
    int u = 0, v = 0;
    for (v = 0; v < h; v += 1)
    {
        for (u = 0; u < w; u += 1)
        {
            // Calculate the offset
            int pos = (v * w * 4) + (u * 4);

            // Grab the r, g, b data for the current pixel
            double pixel_rgb[3] = {
                buffer[pos],
                buffer[pos + 1],
                buffer[pos + 2]
            };

            // If the current pixel's RGB data matches the specified color key...
            if ( (color_key[0] == pixel_rgb[0]) && (color_key[1] == pixel_rgb[1]) && (color_key[2] == pixel_rgb[2]) )
            {
                // Then we're going to set that to 0 alpha in the texture data buffer we grabbed (0 being fully transparent)
                buffer[pos + 3] = 0;
            }
        }
    }

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // We're done with the buffer
    free(buffer);
}


// Replace one color (color1) on a texture with a new color (color2)
void creplace_color_on_texture(int texture_id, int w, int h, double color1[], double color2[])
{
    // Allocate the memory we'll need
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Get the data from that texture
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // Loop through each pixel in the texture data buffer (4 bytes apiece, rgb and alpha)
    int u = 0, v = 0;
    for (v = 0; v < h; v += 1)
    {
        for (u = 0; u < w; u += 1)
        {
            // Calculate the offset
            int pos = (v * w * 4) + (u * 4);

            // Grab the r, g, b data for the current pixel
            double pixel_rgb[3] = {
                buffer[pos],
                buffer[pos + 1],
                buffer[pos + 2]
            };

            // If the current pixel's RGB data matches the specified color key...
            if ( (color1[0] == pixel_rgb[0]) && (color1[1] == pixel_rgb[1]) && (color1[2] == pixel_rgb[2]) )
            {
                // ...then we're going to update it to the new color.
                buffer[pos] = color2[0];
                buffer[pos + 1] = color2[1];
                buffer[pos + 2] = color2[2];
            }
        }
    }

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // We're done with the buffer
    free(buffer);
}


void capply_greyscale_effect_to_screen(int x, int y, int w, int h, double percent)
{
    // Allocate memory
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Read pixel data from pixel buffer
    glReadPixels(x, y, w, h, GL_RGBA, GL_UNSIGNED_BYTE, buffer);


    // Loop through each pixel in the data buffer (4 bytes apiece, rgb and alpha)
    int i = 0, u = 0, v = 0;
    for (v = 0; v < h; v += 1)
    {
        for (u = 0; u < w; u += 1)
        {
            // Calculate the offset
            int pos = (v * w * 4) + (u * 4);

            // Grab the r, g, b data for the current pixel
            double pixel_rgb[3] = {
                buffer[pos],
                buffer[pos + 1],
                buffer[pos + 2]
            };

            // Determine the target value for each channel to create a full greyscale effect
            double pixel_value = ( (0.3 * pixel_rgb[0]) + (0.59 * pixel_rgb[1]) + (0.11 * pixel_rgb[2]) );

            // Obey the strength of the effect, moving each channel's value n% toward "pixel_value"
            for (i = 0; i < 3; i += 1)
            {
                if (pixel_rgb[i] > pixel_value)
                {
                    buffer[pos + i] -= percent * (pixel_rgb[i] - pixel_value);
                }

                else if (pixel_rgb[i] < pixel_value)
                {
                    buffer[pos + i] += percent * (pixel_value - pixel_rgb[i]);
                }
            }
        }
    }


    // Set GL cursor location
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Update the pixel buffer with the revised data
    glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, buffer);


    // Release the memory we allocated
    free(buffer);
}


void capply_radial_greyscale_effect_to_screen(int x, int y, int w, int h, double percent, int angle)
{
    // We'll apply the effect in quadrants; let's determine quadrant size...
    int qw = (w / 2);
    int qh = (h / 2);


    // Start from midnight and move clockwise
    int i = 0, prefilled_quadrant_count = (angle / 90);
    for (i = 0; i < prefilled_quadrant_count; i += 1)
    {
        // Render position for this quadrant
        int rx = x, ry = y;

        // Eastern hemisphere quadrant?
        if (i <= 1)
        {
            rx += qw;
        }

        // Southern hemisphere quadrant?
        if (i > 0 && i < 3)
        {
            ry += qh;
        }

        // Apply the greyscale effect
        capply_greyscale_effect_to_screen(rx, ry, qw, qh, percent);
    }


    // Maybe we don't need to render any more?
    if (angle % 90 == 0)
    {
        return;
    }

    // Otherwise, we will now focus on the final quadrant.  We will apply some clipping planes for this final pass.
    else
    {
        // Determine final quadrant index
        int current_quadrant = (angle / 90);


        // Determine initial rendering position
        int rx = 0, ry = 0;

        // Eastern hemispheree?
        if (current_quadrant <= 1)
        {
            rx += qw;
        }

        // Southern hemisphere?
        if (current_quadrant > 0 && current_quadrant < 3)
        {
            ry += qh;
        }


        // Prepare to define clipping planes
        glLoadIdentity();
        glTranslatef( (x + qw), (y + qh), 0 );

        // Clipping plane 1:  west / east hemisphere?
        if (current_quadrant <= 1)
        {
            double equation[4] = {0, 1, 0, 0};
            glClipPlane(GL_CLIP_PLANE1, equation);
        }

        else
        {
            double equation[4] = {0, 1, 0, 1};
            glClipPlane(GL_CLIP_PLANE1, equation);
        }

        // Clipping plane 2:  north / south hemisphere?
        if (current_quadrant > 0 && current_quadrant < 3)
        {
            double equation[4] = {1, 0, 0, 0};
            glClipPlane(GL_CLIP_PLANE2, equation);
        }

        else
        {
            double equation[4] = {1, 0, 0, 1};
            glClipPlane(GL_CLIP_PLANE2, equation);
        }


        // Clipping plane 3:  angular plane
        if (1)
        {
            glRotatef( (angle % 90), 0, 0, 1 );

            double equation[4] = {1, 0, 0, 1};
            glClipPlane(GL_CLIP_PLANE3, equation);
        }

        glEnable(GL_CLIP_PLANE1);
        glEnable(GL_CLIP_PLANE2);
        glEnable(GL_CLIP_PLANE3);

        capply_greyscale_effect_to_screen(rx, ry, qw, qh, percent);

        glDisable(GL_CLIP_PLANE1);
        glDisable(GL_CLIP_PLANE2);
        glDisable(GL_CLIP_PLANE3);
    }
}



// Apply a greyscale effect to a texture
void capply_greyscale_effect_to_texture(int texture_id, int w, int h, double percent)
{
    // Allocate the memory we'll need
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Get the data from that texture
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);


    // Loop through each pixel in the texture data buffer (4 bytes apiece, rgb and alpha)
    int i = 0, u = 0, v = 0;
    for (v = 0; v < h; v += 1)
    {
        for (u = 0; u < w; u += 1)
        {
            // Calculate the offset
            int pos = (v * w * 4) + (u * 4);

            // Grab the r, g, b data for the current pixel
            double pixel_rgb[3] = {
                buffer[pos],
                buffer[pos + 1],
                buffer[pos + 2]
            };

            // Determine the target value for each channel to create a full greyscale effect
            double pixel_value = ( (0.3 * pixel_rgb[0]) + (0.59 * pixel_rgb[1]) + (0.11 * pixel_rgb[2]) );

            // Obey the strength of the effect, moving each channel's value n% toward "pixel_value"
            for (i = 0; i < 3; i += 1)
            {
                if (pixel_rgb[i] > pixel_value)
                {
                    buffer[pos + i] -= percent * (pixel_rgb[i] - pixel_value);
                }

                else if (pixel_rgb[i] < pixel_value)
                {
                    buffer[pos + i] += percent * (pixel_value - pixel_rgb[i]);
                }
            }
        }
    }

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // We're done with the buffer
    free(buffer);
}


// Clone a texture into a new texture and return the ID
int ccopy_texture_to_texture(int texture_id1, int texture_id2, int w, int h)
{
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id1);

    // Get the data from that texture
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);


    // Let's copy that data over to the other texture...
    glBindTexture(GL_TEXTURE_2D, texture_id2);
    // Misc params for destination
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // We're done with the buffer
    free(buffer);
}


// Clone a texture into a new texture and return the ID
int cclone_texture(int texture_id1, int w, int h)
{
    // Generate a new texture id (for the copy destination)
    int texture_id = 0;
    glGenTextures(1, &texture_id);


    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Bind the original texture
    glBindTexture(GL_TEXTURE_2D, texture_id1);

    // Get the data from that texture
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);


    // Let's copy that data over to the new texture...
    glBindTexture(GL_TEXTURE_2D, texture_id);
    // Misc params for destination
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // We're done with the buffer
    free(buffer);


    // Return the new texture ID
    return texture_id;
}


// Specify a rectangular region of visibility on a texture; the rest gets
// set to alpha 0 (fully transparent)
void cset_visible_region_on_texture(int texture_id, int w, int h, int rect[])
{
    // Allocate memory
    GLubyte *buffer = (GLubyte *) malloc(w * h * 4);

    // Bind the texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Get the data from the texture
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // Loop through and set alpha to 0 or 1, according to whether or not
    // it falls within the visibility region...
    int u = 0, v = 0;
    for (v = 0; v < h; v += 1)
    {
        for (u = 0; u < w; u += 1)
        {
            // Calculate memory offset
            int pos = (v * w * 4) + (u * 4);

            // Are we within the visibility region?
            if ( (u >= rect[0]) && (u < (rect[0] + rect[2])) &&
                 (v >= rect[1]) && (v < (rect[1] + rect[3])) )
            {
                // Visible
                buffer[pos + 3] = 255;
            }

            // Nope; hide this pixel
            else
            {
                // Not visible
                buffer[pos + 3] = 0;
            }
        }
    }

    // Misc params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Send in the image data
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);

    // We're done with the buffer
    free(buffer);
}


// Reset gl cursor
void cload_identity()
{
    glLoadIdentity();
}


// Place gl cursor
void cplace_gl_cursor(int x, int y)
{
    glLoadIdentity();
    glTranslatef(x, y, 0);
}


// Bind texture id
void cset_texture(int texture_id)
{
    glBindTexture(GL_TEXTURE_2D, texture_id);
}


// Begin rendering
void cgl_begin(int param)
{
    glBegin(param);
}


// Begin quad strip
void cgl_begin_quad()
{
    glBegin(GL_QUAD_STRIP);
}


// End rendering
void cgl_end()
{
    glEnd();
}


// Set color
void cgl_color(double color[])
{
    glColor4f(color[0], color[1], color[2], color[3]);
}


void cdraw_texture(int texture_id, int x, int y, int w, int h, double color[])
{
    glLoadIdentity();
    glTranslatef(x, y, 0);

    glColor4f(color[0], color[1], color[2], color[3]);
    //glColor4f(0, 1, 0, 1);

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glBegin(GL_QUAD_STRIP);

    glTexCoord2f(0, 0);
    glVertex2f(0, h);

    glTexCoord2f(0, 1);
    glVertex2f(0, 0);

    glTexCoord2f(1, 0);
    glVertex2f(w, h);

    glTexCoord2f(1, 1);
    glVertex2f(w, 0);

    glEnd();

    return;
}


void cdraw_texture_with_gradient(int texture_id, int x, int y, int w, int h, double color1[], double color2[])
{
    glLoadIdentity();
    glTranslatef(x, y, 0);

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glBegin(GL_QUAD_STRIP);

    glColor4f(color1[0], color1[1], color1[2], color1[3]);

    glTexCoord2f(0, 0);
    glVertex2f(0, h);

    glTexCoord2f(0, 1);
    glVertex2f(0, 0);

    glColor4f(color2[0], color2[1], color2[2], color2[3]);

    glTexCoord2f(1, 0);
    glVertex2f(w, h);

    glTexCoord2f(1, 1);
    glVertex2f(w, 0);

    glEnd();

    return;
}


void cdraw_texture_with_tex_coords(int texture_id, int x, int y, int w, int h, double tu, double tv, double tstepX, double tstepY, double color[])
{
    glLoadIdentity();
    glTranslatef(x, y, 0);

    glColor4f(color[0], color[1], color[2], color[3]);

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glBegin(GL_QUAD_STRIP);

    glTexCoord2f(tu, tv);
    glVertex2f(0, h);

    glTexCoord2f(tu, tv + tstepY);
    glVertex2f(0, 0);

    glTexCoord2f(tu + tstepX, tv);
    glVertex2f(w, h);

    glTexCoord2f(tu + tstepX, tv + tstepY);
    glVertex2f(w, 0);

    glEnd();

    return;
}


void cdraw_texture_with_tex_coords_and_gradient(int texture_id, int x, int y, int w, int h, double tu, double tv, double tstepX, double tstepY, double color1[], double color2[])
{
    glLoadIdentity();
    glTranslatef(x, y, 0);

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glColor4f(color1[0], color1[1], color1[2], color1[3]);

    glBegin(GL_QUAD_STRIP);

    glTexCoord2f(tu, tv);
    glVertex2f(0, h);

    glTexCoord2f(tu, tv + tstepY);
    glVertex2f(0, 0);

    glColor4f(color2[0], color2[1], color2[2], color2[3]);

    glTexCoord2f(tu + tstepX, tv);
    glVertex2f(w, h);

    glTexCoord2f(tu + tstepX, tv + tstepY);
    glVertex2f(w, 0);

    glEnd();

    return;
}


void cdraw_rotated_texture_with_tex_coords(double degrees, int texture_id, int x, int y, int w, int h, double tu, double tv, double tstepX, double tstepY, double color[])
{
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Rotation
    if (degrees != 0.0)
    {
        glTranslatef(w/2, h/2, 0);
        glRotatef(degrees, 0, 0, 1);
        glTranslatef(-w/2, -h/2, 0);
    }

    glColor4f(color[0], color[1], color[2], color[3]);

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glBegin(GL_QUAD_STRIP);

    glTexCoord2f(tu, tv);
    glVertex2f(0, h);

    glTexCoord2f(tu, tv + tstepY);
    glVertex2f(0, 0);

    glTexCoord2f(tu + tstepX, tv);
    glVertex2f(w, h);

    glTexCoord2f(tu + tstepX, tv + tstepY);
    glVertex2f(w, 0);

    glEnd();

    return;
}


// Skip load identity / translatef
void cdraw_texture_in_place_with_tex_coords(int texture_id, int x, int y, int w, int h, double texture_coords[])
{
    glTexCoord2f(texture_coords[0], texture_coords[1]);
    glVertex2f(x, y + h);

    glTexCoord2f(texture_coords[0], texture_coords[1] + texture_coords[3]);
    glVertex2f(x, y);

    glTexCoord2f(texture_coords[0] + texture_coords[2], texture_coords[1]);
    glVertex2f(x + w, y + h);

    glTexCoord2f(texture_coords[0] + texture_coords[2], texture_coords[1] + texture_coords[3]);
    glVertex2f(x + w, y);

    return;
}


// Clip a given region of the frame buffer.
// Returns:  gl texture id
int cclip_backbuffer(int x, int y, int texture_size)
{
    // Generate texture id
    int texture_id = 0;
    glGenTextures(1, &texture_id);

    // Bind texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Stuff
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Copy the appropriate region of data to the texture...
    glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, x, y, texture_size, texture_size, 0);

    // Return texture id
    return texture_id;
}


// Draw a triangle at a given orientation
void cdraw_triangle_with_border(int x, int y, int w, int h, double background_color[], double border_color[], int orientation)
{
    // Position
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Turn off textures, draw colored primitive
    glDisable(GL_TEXTURE_2D);

    // Render border
    int padding = 1;

    // Border color
    glColor4f(
        border_color[0],
        border_color[1],
        border_color[2],
        border_color[3]
    );

    // Render triangle primitive
    glBegin(GL_TRIANGLE_STRIP);


    // How to orient the triangle?
    if (orientation == DIR_UP)
    {
        glVertex2f(-padding, h + padding);
        glVertex2f((w / 2), -padding);
        glVertex2f(w + padding, h + padding);
    }

    else if (orientation == DIR_RIGHT)
    {
        glVertex2f(-padding, -padding);
        glVertex2f(-padding, h + padding);
        glVertex2f(w + padding, (h / 2));
    }

    else if (orientation == DIR_DOWN)
    {
        glVertex2f(-padding, -padding);
        glVertex2f((w / 2), h + padding);
        glVertex2f(w + padding, -padding);
    }

    else if (orientation == DIR_LEFT)
    {
        glVertex2f(w + padding, -padding);
        glVertex2f(w + padding, h + padding);
        glVertex2f(-padding, (h / 2));
    }


    // Done!
    glEnd();


    // Background color
    glColor4f(
        background_color[0],
        background_color[1],
        background_color[2],
        background_color[3]
    );


    // Render triangle primitive
    glBegin(GL_TRIANGLE_STRIP);


    // How to orient?
    if (orientation == DIR_UP)
    {
        glVertex2f(0, h);
        glVertex2f((w / 2), 0);
        glVertex2f(w, h);
    }

    else if (orientation == DIR_RIGHT)
    {
        glVertex2f(0, 0);
        glVertex2f(0, h);
        glVertex2f(w, (h / 2));
    }

    else if (orientation == DIR_DOWN)
    {
        glVertex2f(0, 0);
        glVertex2f((w / 2), h);
        glVertex2f(w, 0);
    }

    else if (orientation == DIR_LEFT)
    {
        glVertex2f(w, 0);
        glVertex2f(w, h);
        glVertex2f(0, (h / 2));
    }


    // Done!
    glEnd();

    // Reactive texture rendering
    glEnable(GL_TEXTURE_2D);

    // Full color heading forward
    glColor4f(1, 1, 1, 1.0);
}


// Draw a triangle at a given orientation with no border
void cdraw_triangle_without_border(int x, int y, int w, int h, double background_color[], int orientation)
{
    // Position
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Turn off textures, draw colored primitive
    glDisable(GL_TEXTURE_2D);


    // Background color
    glColor4f(
        background_color[0],
        background_color[1],
        background_color[2],
        background_color[3]
    );


    // Render triangle primitive
    glBegin(GL_TRIANGLE_STRIP);


    // How to orient?
    if (orientation == DIR_UP)
    {
        glVertex2f(0, h);
        glVertex2f((w / 2), 0);
        glVertex2f(w, h);
    }

    else if (orientation == DIR_RIGHT)
    {
        glVertex2f(0, 0);
        glVertex2f(0, h);
        glVertex2f(w, (h / 2));
    }

    else if (orientation == DIR_DOWN)
    {
        glVertex2f(0, 0);
        glVertex2f((w / 2), h);
        glVertex2f(w, 0);
    }

    else if (orientation == DIR_LEFT)
    {
        glVertex2f(w, 0);
        glVertex2f(w, h);
        glVertex2f(0, (h / 2));
    }


    // Done!
    glEnd();

    // Reactive texture rendering
    glEnable(GL_TEXTURE_2D);

    // Full color heading forward
    glColor4f(1, 1, 1, 1.0);
}


// Render a "fill pattern" as a previously-dug hole begins to fill in...
void cdraw_fill_pattern(int x, int y, int tile, int tile_width, int tile_height, int tilesheet_texture_id, double tilesheet_texture_coords[], int frame, int fill_texture_id, double fill_texture_coords[], double color[])
{
    // Position
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Render the tile first
    glBindTexture(GL_TEXTURE_2D, tilesheet_texture_id);

    // Set color
    glColor4f(
        color[0],
        color[1],
        color[2],
        color[3]
    );

    // Render quad
    glBegin(GL_QUAD_STRIP);


    // Set quad vertices
    glTexCoord2f(tilesheet_texture_coords[0], tilesheet_texture_coords[1]);
    glVertex2f(0, tile_height);

    glTexCoord2f(tilesheet_texture_coords[0], tilesheet_texture_coords[1] + tilesheet_texture_coords[3]);
    glVertex2f(0, 0);

    glTexCoord2f(tilesheet_texture_coords[0] + tilesheet_texture_coords[2], tilesheet_texture_coords[1]);
    glVertex2f(tile_width, tile_height);

    glTexCoord2f(tilesheet_texture_coords[0] + tilesheet_texture_coords[2], tilesheet_texture_coords[1] + tilesheet_texture_coords[3]);
    glVertex2f(tile_width, 0);


    // Finally!
    glEnd();


    // Now render the pattern fill overlay
    glBindTexture(GL_TEXTURE_2D, fill_texture_id);

    // Render quad
    glBegin(GL_QUAD_STRIP);


    // Set quad vertices
    glTexCoord2f(fill_texture_coords[0], fill_texture_coords[1]);
    glVertex2f(0, tile_height);

    glTexCoord2f(fill_texture_coords[0], fill_texture_coords[1] + fill_texture_coords[3]);
    glVertex2f(0, 0);

    glTexCoord2f(fill_texture_coords[0] + fill_texture_coords[2], fill_texture_coords[1]);
    glVertex2f(tile_width, tile_height);

    glTexCoord2f(fill_texture_coords[0] + fill_texture_coords[2], fill_texture_coords[1] + fill_texture_coords[3]);
    glVertex2f(tile_width, 0);


    // Finally!
    glEnd();
}


// Render a particle (based off of a tilesheet tile)
void cdraw_particle(int x, int y, int w, int h, int index_x, int index_y, double degrees, int tile, int tilesheet_texture_id, double tilesheet_texture_coords[], double color[])
{
    // Position
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Rotation
    if (degrees != 0.0)
    {
        glRotatef(degrees, 0, 0, 1);
    }

    // Bind texture
    glBindTexture(GL_TEXTURE_2D, tilesheet_texture_id);

    // Set color
    glColor4f(color[0], color[1], color[2], color[3]);


    // Render quad
    glBegin(GL_QUAD_STRIP);


    // Plot vertices
    glTexCoord2f(tilesheet_texture_coords[0], tilesheet_texture_coords[1]);
    glVertex2f(0, h);

    glTexCoord2f(tilesheet_texture_coords[0], tilesheet_texture_coords[1] + tilesheet_texture_coords[3]);
    glVertex2f(0, 0);

    glTexCoord2f(tilesheet_texture_coords[0] + tilesheet_texture_coords[2], tilesheet_texture_coords[1]);
    glVertex2f(w, h);

    glTexCoord2f(tilesheet_texture_coords[0] + tilesheet_texture_coords[2], tilesheet_texture_coords[1] + tilesheet_texture_coords[3]);
    glVertex2f(w, 0);


    // At last!
    glEnd();
}


// Stash the current clipping state (scissor, stencil)
void cpause_clipping()
{
    //glPushAttrib(GL_SCISSOR_BIT | GL_STENCIL_BUFFER_BIT);

    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_STENCIL_TEST);
}


// Revert to the previous clipping state
void cresume_clipping()
{
    //glPopAttrib();

    glEnable(GL_STENCIL_TEST);
    glEnable(GL_SCISSOR_TEST);
}


void cstencil_enable()
{
    glEnable(GL_STENCIL_TEST);
}


void cstencil_disable()
{
    glDisable(GL_STENCIL_TEST);
}


void cstencil_enable_painting()
{
    glClearStencil(0x0);
    // Config
    glStencilMask(0x1);

    // We want to always allow writes to the framebuffer
    glStencilFunc(GL_ALWAYS, 0x1, 0x1);

    // And we want to always update the stencil buffer
    glStencilOp(GL_REPLACE, GL_REPLACE, GL_REPLACE);

    //glClearStencil(0x0);

    // Enable stencil test
    //glEnable(GL_STENCIL_TEST);
}


void cstencil_enable_erasing()
{
    glStencilMask(0x1);

    // Always overwrite stencil buffer
    glStencilFunc(GL_ALWAYS, 0x1, 0x1);

    // Also erase stencil buffer values
    glStencilOp(GL_ZERO, GL_ZERO, GL_ZERO);
}


void cstencil_enforce_painted_only()
{
    // Config
    glStencilMask(0x1);

    // Only allow writes where we've previously drawn on the stencil buffer
    glStencilFunc(GL_EQUAL, 0x1, 0x1);

    // Always keep original stencil buffer value
    glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP);
}


void cdisable_stencil_test()
{
    glDisable(GL_STENCIL_TEST);
}


// Clear a region of the stencil buffer
void cstencil_clear_region(int x, int y, int w, int h)
{
    // Prevent any framebuffer modification
    glColorMask(0, 0, 0, 0);

    // Not sure what this does, but I need it.  Sorry...
    glStencilMask(0x1);

    // Always succeed, we're clearing the region with 0x0s
    glStencilFunc(GL_ALWAYS, 0x0, 0x1);

    // Always clear the stencil buffer for the given region
    glStencilOp(GL_ZERO, GL_ZERO, GL_ZERO);

    // Start at 0, 0
    glLoadIdentity();

    // Move to position
    glTranslatef(x, y, 0);

    // "Draw" a rectangle (won't render anything)
    glRecti(0, 0, w, h);

    // Allow color modification to resume
    glColorMask(1, 1, 1, 1);
}


// Clear the entire stencil buffer
void cstencil_clear()
{
    cstencil_clear_region(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
}


// Draw rectangle
void cdraw_rect(int x, int y, int w, int h, double color[])
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);

    // color
    glColor4f(color[0], color[1], color[2], color[3]);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Draw the rectangle
    glRecti(0, 0, w, h);

    // back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
    
    // Definitely turn texturing back on
    glEnable(GL_TEXTURE_2D);
}


void cdraw_rect2(int x, int y, int w, int h, double color[])
{

    cdraw_rect(x, y, w, h, color);

    glDisable(GL_TEXTURE_2D);


    //cstencil_clear_region(0, 0, 100, 100);


    glClear(GL_STENCIL_BUFFER_BIT);//Stencil(0x0);
    glClearStencil(0x0);


    glStencilMask(0x1);

    glEnable(GL_STENCIL_TEST);


    glStencilFunc(GL_ALWAYS, 0x1, 0x1);
    glStencilOp(GL_REPLACE, GL_REPLACE, GL_REPLACE);

    glColorMask(0, 0, 0, 0);
    double color2[] = {1.0, 0, 0, 1.0};
    cdraw_rect(x + 40, y + 40, w - 80, h - 80, color2);
    glColorMask(1, 1, 1, 1);


    cstencil_clear_region(x, y, w / 2, h / 2);


    glStencilFunc(GL_NOTEQUAL, 0x1, 0x1);
    glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP);

    double color3[] = {0.9, 0.1, 0.1, 1.0};


    if (glIsEnabled(GL_STENCIL_TEST)) { color3[0] = 0.1; color3[2] = 0.9; }
    cdraw_rect(x + 20, y + 20, w - 40, h - 40, color3);




    glDisable(GL_STENCIL_TEST);

    glEnable(GL_TEXTURE_2D);
}


void cdraw_rect_frame(int x, int y, int w, int h, double color[], int frame_size)
{
    // Turn off texturing so that we can render plain color
    glDisable(GL_TEXTURE_2D);

    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // color
    glColor4f(color[0], color[1], color[2], color[3]);

    // Draw four rects to create a frame
    glRecti(0, 0, w, frame_size); // top
    glRecti(w - frame_size, 0, w, h); // right
    glRecti(0, h - frame_size, w, h); // bottom
    glRecti(0, 0, frame_size, h); // left

    // back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);

    // Definitely turn texturing back on
    glEnable(GL_TEXTURE_2D);
}


void cdraw_rect_with_horizontal_gradient(int x, int y, int w, int h, double color1[], double color2[])
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);

    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(x, y, 0);

    //glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    //glPush
    //glBlendFunc(GL_SRC_ALPHA, GL_ONE);



    // Draw the rectangle
    glBegin(GL_QUAD_STRIP);

    glColor4f(color1[0], color1[1], color1[2], color1[3]);
    glTexCoord2f(0, 0);
    glVertex2f(0, h);

    glTexCoord2f(0, 1);
    glVertex2f(0, 0);

    glColor4f(color2[0], color2[1], color2[2], color2[3]);
    glTexCoord2f(1, 0);
    glVertex2f(w, h);

    glTexCoord2f(1, 1);
    glVertex2f(w, 0);

    glEnd();

    //glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    // back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
    
    // Definitely turn texturing back on
    glEnable(GL_TEXTURE_2D);
}


void cdraw_rect_with_vertical_gradient(int x, int y, int w, int h, double color1[], double color2[])
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);

    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(x, y, 0);

    // Draw the rectangle
    glBegin(GL_QUAD_STRIP);

    glColor4f(color2[0], color2[1], color2[2], color2[3]);
    glTexCoord2f(0, 0);
    glVertex2f(0, h);

    glColor4f(color1[0], color1[1], color1[2], color1[3]);
    glTexCoord2f(0, 1);
    glVertex2f(0, 0);

    glColor4f(color2[0], color2[1], color2[2], color2[3]);
    glTexCoord2f(1, 0);
    glVertex2f(w, h);

    glColor4f(color1[0], color1[1], color1[2], color1[3]);
    glTexCoord2f(1, 1);
    glVertex2f(w, 0);

    glEnd();

    //glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    // back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
    
    // Definitely turn texturing back on
    glEnable(GL_TEXTURE_2D);
}


void cdraw_rect_with_horizontal_gradient_upon_existing_stencil_buffer(int x, int y, int w, int h, double color1[], double color2[])
{
    // Config
    //glStencilMask(0x1);

    // We only want to render in areas where we have previously rendered to the stencil buffer...
    //glStencilFunc(GL_EQUAL, 0x1, 0x1);
    //glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP);

    // Render an ordinary rectangle with the desired gradient...
    cdraw_rect_with_horizontal_gradient(x, y, w, h, color1, color2);
}


void cdraw_circle(int cx, int cy, int radius, double color[], int accuracy, int start, int end)
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(cx, cy, 0);

    // color
    glColor4f(color[0], color[1], color[2], color[3]);

    // Begin quad strip
    //glBegin(GL_QUAD_STRIP);
    glBegin(GL_TRIANGLE_FAN);

    // Center of fan (center of circle)
    glVertex2f( 0 , 0 );

    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        // Trailing and leading perimeter points
        glVertex2f( cos( degrees_to_radians(i) ) * (radius) , sin( degrees_to_radians(i) ) * (radius) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius) , sin( degrees_to_radians(i + accuracy) ) * (radius) );
    }

    // Done!
    glEnd();

    // Turn texturing back on...
    glEnable(GL_TEXTURE_2D);

    // Back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
}


void cdraw_circle_with_gradient(int cx, int cy, int radius, double color1[], double color2[], int accuracy, int start, int end)
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(cx, cy, 0);

    // Begin quad strip
    glBegin(GL_TRIANGLE_FAN);


    // The center vertices will always have the same color.
    double colorCenter[] = {
        (color1[0] + color2[0]) / 2.0,
        (color1[1] + color2[1]) / 2.0,
        (color1[2] + color2[2]) / 2.0
    };


    // Define the fan's origin, which always uses the same color and everything
    glColor4f(colorCenter[0], colorCenter[1], colorCenter[2], color1[3]);
    glVertex2f( 0 , 0 );

    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        // Calculate the blend percentage (from start color to end color) for the perimeter points.
        double blend1 = ((cos( degrees_to_radians(i) ) + 1.0) / 2.0);
        double blend2 = ((cos( degrees_to_radians(i + accuracy) ) + 1.0) / 2.0);

        // Define the color for the initial perimeter vertex
        double colorPerimeter1[] = {
             color1[0] + (blend1 * (color2[0] - color1[0])),
             color1[1] + (blend1 * (color2[1] - color1[1])),
             color1[2] + (blend1 * (color2[2] - color1[2]))
        };

        // The next perimeter vertex moves forward along the circle's perimeter, so the color varies slightly...
        double colorPerimeter2[] = {
             color1[0] + (blend2 * (color2[0] - color1[0])),
             color1[1] + (blend2 * (color2[1] - color1[1])),
             color1[2] + (blend2 * (color2[2] - color1[2]))
        };

        // Define the current fan piece (perimeter points, trailing and leading)
        glColor4f(colorPerimeter1[0], colorPerimeter1[1], colorPerimeter1[2], color2[3]);
        glVertex2f( cos( degrees_to_radians(i) ) * (radius) , sin( degrees_to_radians(i) ) * (radius) );

        glColor4f(colorPerimeter2[0], colorPerimeter2[1], colorPerimeter2[2], color2[3]);
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius) , sin( degrees_to_radians(i + accuracy) ) * (radius) );
    }

    // Done!
    glEnd();

    // Turn texturing back on...
    glEnable(GL_TEXTURE_2D);

    // Back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
}


void cdraw_circle_with_border(int cx, int cy, int radius, double color[], int accuracy, int start, int end, double border_color[], int border_size)
{
    // Draw a circle first...
    cdraw_circle(cx, cy, radius, color, accuracy, start, end);


    // Disable texturing as we proceed to render a border...
    glDisable(GL_TEXTURE_2D);

    // Begin a line loop
    glBegin(GL_LINE_LOOP);

    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        glVertex2f((cos(degrees_to_radians(i)) * radius), (sin(degrees_to_radians(i)) * radius));
    }

    // End the line loop
    glEnd();

    // Re-enable texturing
    glEnable(GL_TEXTURE_2D);

    // Full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
}


void cdraw_circle_with_radial_gradient(int cx, int cy, int radius, double color1[], double color2[], int accuracy, int start, int end)
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(cx, cy, 0);

    // color
    glColor4f(color1[0], color1[1], color1[2], color1[3]);

    // Begin quad strip
    //glBegin(GL_QUAD_STRIP);
    glBegin(GL_TRIANGLE_FAN);

    // Center of fan (center of circle)
    glVertex2f( 0 , 0 );

    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        // Trailing and leading perimeter points
        glColor4f(color2[0], color2[1], color2[2], color2[3]);
        glVertex2f( cos( degrees_to_radians(i) ) * (radius) , sin( degrees_to_radians(i) ) * (radius) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius) , sin( degrees_to_radians(i + accuracy) ) * (radius) );
    }

    // Done!
    glEnd();

    // Turn texturing back on...
    glEnable(GL_TEXTURE_2D);

    // Back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);
}


void cdraw_exclusive_circle_with_radial_gradient(int cx, int cy, int radius, double color1[], double color2[], int accuracy, int start, int end)
{
    // Config
    glStencilMask(0x0);

    // Clear the region we'll be rendering on... for now it's all good...
    glClearStencil(0x0);

    glStencilMask(0x1);

    // Now make sure the stencil test always passes...
    glStencilFunc(GL_ALWAYS, 0x1, 0x1);

    // ... and always imprints upon the stencil buffer...
    glStencilOp(GL_REPLACE, GL_REPLACE, GL_REPLACE);

    // Enable stencil test
    glEnable(GL_STENCIL_TEST);


    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(cx, cy, 0);

    // color
    glColor4f(color1[0], color1[1], color1[2], color1[3]);

    // Begin triangle fan
    glBegin(GL_TRIANGLE_FAN);

    // Center of fan (center of circle)
    glVertex2f( 0 , 0 );

    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        // Trailing and leading perimeter points
        glColor4f(color2[0], color2[1], color2[2], color2[3]);
        glVertex2f( cos( degrees_to_radians(i) ) * (radius) , sin( degrees_to_radians(i) ) * (radius) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius) , sin( degrees_to_radians(i + accuracy) ) * (radius) );
    }

    // Done!
    glEnd();

    // Turn texturing back on...
    glEnable(GL_TEXTURE_2D);

    // Back to full color
    glColor4f(1.0, 1.0, 1.0, 1.0);


    // Now we're going to lay a rectangle upon the non-exclusive area.  Thanks to the stencil
    // test, though, it will only affect the non-exclusive region (leaving the defined circle unmodified).
    glStencilFunc(GL_NOTEQUAL, 0x1, 0x1);
    glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP);

    // Render an ordinary rectangle with the desired gradient...
    cdraw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, color2);

    // Finally, we are done with the stencil tests...
    glDisable(GL_STENCIL_TEST);
}


void cdraw_radial_arc(int cx, int cy, int start, int end, int radius, int thickness, double color[], int accuracy)
{
    // Fill the background
    //cdraw_circle(cx, cy, radius, background, accuracy, start, end);


    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(cx, cy, 0);

    // color
    glColor4f(color[0], color[1], color[2], color[3]);

    // Begin quad strip
    glBegin(GL_QUAD_STRIP);

    // Loop
    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        glVertex2f( cos( degrees_to_radians(i) ) * (radius - thickness) , sin( degrees_to_radians(i) ) * (radius - thickness) );
        glVertex2f( cos( degrees_to_radians(i) ) * (radius) , sin( degrees_to_radians(i) ) * (radius) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius - thickness) , sin( degrees_to_radians(i + accuracy) ) * (radius - thickness) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius) , sin( degrees_to_radians(i + accuracy) ) * (radius) );
    }

    // Done!
    glEnd();

    // Re-enable texturing
    glEnable(GL_TEXTURE_2D);
}


void cdraw_radial_arc_with_gradient(int cx, int cy, int start, int end, int radius, int thickness, double background1[], double background2[], double color[], int accuracy)
{
    // Fill the background
    //cdraw_circle_with_gradient(cx, cy, radius, background1, background2, accuracy, start, end);


    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(cx, cy, 0);

    // color
    glColor4f(color[0], color[1], color[2], color[3]);

    // Begin quad strip
    glBegin(GL_QUAD_STRIP);

    // Loop
    int i = 0;
    for (i = start; i < end; i += accuracy)
    {
        glVertex2f( cos( degrees_to_radians(i) ) * (radius - thickness) , sin( degrees_to_radians(i) ) * (radius - thickness) );
        glVertex2f( cos( degrees_to_radians(i) ) * (radius) , sin( degrees_to_radians(i) ) * (radius) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius - thickness) , sin( degrees_to_radians(i + accuracy) ) * (radius - thickness) );
        glVertex2f( cos( degrees_to_radians(i + accuracy) ) * (radius) , sin( degrees_to_radians(i + accuracy) ) * (radius) );
    }

    // Done!
    glEnd();

    // Re-enable texturing
    glEnable(GL_TEXTURE_2D);
}


// Draw line
void cdraw_line(int x1, int y1, int x2, int y2, double color[], int size)
{
    // Turn off texturing so we can render plain color
    glDisable(GL_TEXTURE_2D);
    
    // color
    glColor4f(color[0], color[1], color[2], color[3]);

    // Find the length of the line
    int length = sqrt(( (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1) ));

    double dx = 1.0 * abs(x2 - x1);
    double dy = 1.0 * abs(y2 - y1);

    int base_angle = 0;

    if (x2 <= x1 && y2 > y1)
    {
        base_angle = 90;
    }
    else if (x2 < x1 && y2 <= y1)
    {
        base_angle = 180;
    }
    else if (x2 >= x1 && y2 < y1)
    {
        base_angle = 270;
    }

    // Get the angle of the line
    int angle = 0;

    if (dx != 0)
    {
        angle = radians_to_degrees(atan(dy / dx));

        if (base_angle == 90 || base_angle == 270)
        {
            angle = 90 - angle;
        }
    }

    glDisable(GL_TEXTURE_2D);

    // Reset matrix and move to where we want to draw the thing
    glLoadIdentity();
    glTranslatef(x1, y1, 0);

    glRotatef(base_angle + angle, 0, 0, 1);

    //glTranslatef(0, -1 * ( (size - 1) / 2), 0);

    glRecti(0, 0, length, size);

    glEnable(GL_TEXTURE_2D);
}


void cdraw_rounded_rect(int x, int y, int w, int h, double background[], int radius)
{
    // Northwest
    cdraw_circle(x + radius, y + radius, radius, background, 10, 180, 270);

    // Northeast
    cdraw_circle(x + w - radius, y + radius, radius, background, 10, 270, 360);

    // Southeast
    cdraw_circle(x + w - radius, y + h - radius, radius, background, 10, 0, 90);

    // Southwest
    cdraw_circle(x + radius, y + h - radius, radius, background, 10, 90, 180);

    // North
    cdraw_rect(x + radius, y, w - (2 * radius), radius, background);

    // East
    cdraw_rect( (x + w) - radius, y + radius, radius, h - (2 * radius), background);

    // South
    cdraw_rect(x + radius, y + (h - radius), w - (2 * radius), radius, background);

    // West
    cdraw_rect(x, y + radius, radius, h - (2 * radius), background);


    // Body
    cdraw_rect(x + radius, y + radius, w - (2 * radius), h - (2 * radius), background);
}


void cdraw_rounded_rect_frame(int x, int y, int w, int h, double border[], int border_size, int radius)
{
    // Northwest
    cdraw_radial_arc(x + radius, y + radius, 180, 270, radius, border_size, border, 10);

    // NOrtheast
    cdraw_radial_arc( (x + w) - radius, y + radius, 270, 360, radius, border_size, border, 10);

    // Southeast
    cdraw_radial_arc( (x + w) - radius, (y + h) - radius, 0, 90, radius, border_size, border, 10);

    // Southwest
    cdraw_radial_arc(x + radius, (y + h) - radius, 90, 180, radius, border_size, border, 10);


    // North
    cdraw_rect(x + radius, y, w - (2 * radius), border_size, border);

    // East
    cdraw_rect( (x + w - border_size), y + radius, border_size, h - (2 * radius), border);

    // South
    cdraw_rect(x + radius, y + h - border_size, w - (2 * radius), border_size, border);

    // West
    cdraw_rect(x, y + radius, border_size, h - (2 * radius), border);
}


void cdraw_rounded_rect_with_horizontal_gradient(int x, int y, int w, int h, double background1[], double background2[], int radius)
{
    //cdraw_rect_with_horizontal_gradient(x, y, w, h, background1, background2);
    //return;

    // First let's enable stenciling.  We'll draw the contraption as usual,
    // allowing it to always appear (always pass stencil test), and this will
    // imprint its shape upon the stencil buffer...
    //glEnable(GL_STENCIL_TEST);

    // First let's clear the stencil buffer for the given region
    if (1) {

    glEnable(GL_STENCIL_TEST);

        glClearStencil(0x0);
        glStencilMask(0x1);

        glColorMask(0, 0, 0, 0);
        glStencilOp(GL_ZERO, GL_ZERO, GL_ZERO);
        cdraw_rect(x, y, w, h, background2);
        glColorMask(1, 1, 1, 1);
    }



    // Config
    glStencilMask(0x0);

    // Clear the region we'll be rendering on... for now it's all good...
    //cstencil_clear_region(x, y, w, h);

    glClearStencil(0x0);

    glStencilMask(0x1);

    // Now make sure the stencil test always passes...
    glStencilFunc(GL_ALWAYS, 0x1, 0x1);

    // ... and always imprints upon the stencil buffer...
    glStencilOp(GL_REPLACE, GL_REPLACE, GL_REPLACE);


    glEnable(GL_STENCIL_TEST);

    

    // Now, draw the original geometry
    cdraw_rounded_rect(x, y, w, h, background2, radius);

    //glEnable(GL_STENCIL_TEST);


    // Next we're going to draw an ordinary rectangle (with gradient) on top of the rounded
    // rectangle.  However, we're only going to draw on the areas affected by the previous renders...
    glStencilFunc(GL_EQUAL, 0x1, 0x1);
    glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP);

    // Render an ordinary rectangle with the desired gradient...
    cdraw_rect_with_horizontal_gradient(x, y, w, h, background1, background2);
    //cdraw_rect2(x, y, w, h, background1);


    // Finally, we are done with the stencil tests...
    glDisable(GL_STENCIL_TEST);
}


void cdraw_rounded_rect_with_vertical_gradient(int x, int y, int w, int h, double background1[], double background2[], int radius)
{
    //cdraw_rect_with_horizontal_gradient(x, y, w, h, background1, background2);
    //return;

    // First let's enable stenciling.  We'll draw the contraption as usual,
    // allowing it to always appear (always pass stencil test), and this will
    // imprint its shape upon the stencil buffer...
    //glEnable(GL_STENCIL_TEST);

    // Config
    glStencilMask(0x0);

    // Clear the region we'll be rendering on... for now it's all good...
    //cstencil_clear_region(x, y, w, h);

    glClearStencil(0x0);

    glStencilMask(0x1);

    // Now make sure the stencil test always passes...
    glStencilFunc(GL_ALWAYS, 0x1, 0x1);

    // ... and always imprints upon the stencil buffer...
    glStencilOp(GL_REPLACE, GL_REPLACE, GL_REPLACE);


    glEnable(GL_STENCIL_TEST);


    // Now, draw the original geometry
    cdraw_rounded_rect(x, y, w, h, background2, radius);

    //glEnable(GL_STENCIL_TEST);


    // Next we're going to draw an ordinary rectangle (with gradient) on top of the rounded
    // rectangle.  However, we're only going to draw on the areas affected by the previous renders...
    glStencilFunc(GL_EQUAL, 0x1, 0x1);
    glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP);

    // Render an ordinary rectangle with the desired gradient...
    cdraw_rect_with_vertical_gradient(x, y, w, h, background1, background2);
    //cdraw_rect2(x, y, w, h, background1);


    // Finally, we are done with the stencil tests...
    glDisable(GL_STENCIL_TEST);
}


// Look... I'm not going to lie.  This function is awful.  I hardly even know how it works,
// honestly.  But hey, it works!  Yeah!
void cdraw_clock_rect(int x, int y, int w, int h, double color[], int degrees)
{
    // 12:00
    int ox = x + (w / 2);
    int oy = y;

    int rw = (w / 2);
    int rh = (h / 2);

    int rx = 0;
    int ry = 0;

    // Fill in quadrants that have 100% fill (e.g. 28% fill means a one full quadrant (25%) and one quadrant with 3% fill)
    int i;
    //for (i = 0; i < (degrees - 89); i += 90)
    for (i = 0; i < ( (degrees / 90) ) * 90; i += 90)
    {
        rx = ox;
        ry = oy;

        // When rendering on the left two quadrants (x < 0), we will shift from x = 0 (12:00) to x = -radius (9:00)
        if (i == 180 || i == 270)
        {
            rx -= rw;
        }

        // When rendering on the bottom two quadrants...
        if (i == 90 || i == 180)
        {
            ry += rh;
        }

        cdraw_rect(rx, ry, rw, rh, color);
    }

    // If we're rendering at a multiple of 90, we don't need to process a  partial fill...
    if ( (degrees % 90) == 0 )
    {
        return;
    }

    else
    {
        // Position
        glLoadIdentity();
        glTranslatef(x + rw, y + rh, 0);

        // Prepare to perform partial fill on quadrant that needs it.  Which one is that?
        int block = (degrees / 90);

        // How much fill?
        int angle = (degrees % 90);

        if (block == 0)
        {
            int dx = tan( degrees_to_radians(90 - angle) ) * rh;
            int dy = rh;

            double equation1[4] = {-dx, -dy, 0, 0};
            glClipPlane(GL_CLIP_PLANE1, equation1);

            double equation2[4] = {0, -1, 0, 0};
            glClipPlane(GL_CLIP_PLANE2, equation2);

            glTranslatef(0, -rh, 0);

            double equation3[4] = {1, 0, 0, 0};
            glClipPlane(GL_CLIP_PLANE3, equation3);

            glEnable(GL_CLIP_PLANE1);
            glEnable(GL_CLIP_PLANE2);
            glEnable(GL_CLIP_PLANE3);

            cdraw_rect(ox, oy, rw, rh, color);
        }

        else if (block == 1)
        {
            int dx = tan( degrees_to_radians(angle) ) * rh;
            int dy = rh;

            double equation1[4] = {dx, -dy, 0, 0};
            glClipPlane(GL_CLIP_PLANE1, equation1);

            double equation2[4] = {0, 1, 0, 0};
            glClipPlane(GL_CLIP_PLANE2, equation2);

            glTranslatef(0, rh, 0);

            double equation3[4] = {0, -1, 0, 0};
            glClipPlane(GL_CLIP_PLANE3, equation3);

            glEnable(GL_CLIP_PLANE1);
            glEnable(GL_CLIP_PLANE2);
            glEnable(GL_CLIP_PLANE3);

            cdraw_rect(ox, oy + rh, rw, rh, color);
        }

        else if (block == 2)
        {
            int dx = tan( degrees_to_radians(90 - angle) ) * rh;
            int dy = rh;

            double equation1[4] = {dx, dy, 0, 0};
            glClipPlane(GL_CLIP_PLANE1, equation1);

            double equation2[4] = {0, 1, 0, 0};
            glClipPlane(GL_CLIP_PLANE2, equation2);

            glTranslatef(0, rh, 0);

            double equation3[4] = {0, -1, 0, 0};
            glClipPlane(GL_CLIP_PLANE3, equation3);

            glEnable(GL_CLIP_PLANE1);
            glEnable(GL_CLIP_PLANE2);
            glEnable(GL_CLIP_PLANE3);

            cdraw_rect(ox - rw, oy + rh, rw, rh, color);
        }

        else if (block == 3)
        {
            int dx = rw;
            int dy = tan( degrees_to_radians(90 - angle) ) * rw;

            double equation1[4] = {-dx, dy, 0, 0};
            glClipPlane(GL_CLIP_PLANE1, equation1);

            double equation2[4] = {0, -1, 0, 0};
            glClipPlane(GL_CLIP_PLANE2, equation2);

            glTranslatef(-rw, 0, 0);

            double equation3[4] = {1, 0, 0, 0};
            glClipPlane(GL_CLIP_PLANE3, equation3);

            glEnable(GL_CLIP_PLANE1);
            glEnable(GL_CLIP_PLANE2);
            glEnable(GL_CLIP_PLANE3);

            cdraw_rect(ox - rw, oy, rw, rh, color);
        }

        glDisable(GL_CLIP_PLANE1);
        glDisable(GL_CLIP_PLANE2);
        glDisable(GL_CLIP_PLANE3);
    }
}

// Clear render buffers
void clear_buffers()
{
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
}

// Enable scissor testing
void scissor_on()
{
    glEnable(GL_SCISSOR_TEST);
}

// Disable scissor testing
void scissor_off()
{
    glDisable(GL_SCISSOR_TEST);
}

// Set scissor region
void set_scissor(int x, int y, int w, int h)
{
    // Apply scissor region
    glScissor(x, y, w, h);
}
