#include <GL/gl.h>
#include <GL/glu.h>

//#include "glew.h"

#define STRINGIFY(A) #A

#include "test1v.glsl"
#include "test1f.glsl"


GLuint ccreate_shader_program(const char *vertex_script,  const char *fragment_script)
{
    // Create vertex shader
    GLuint vertex_shader = glCreateShader(GL_VERTEX_SHADER);

    // Load 1 script
    glShaderSource(vertex_shader, 1, (const GLchar**) &vertex_script, 0);

    // Compile vertex shader
    glCompileShader(vertex_shader);


    // Create fragment shader
    GLuint fragment_shader = glCreateShader(GL_FRAGMENT_SHADER);

    // Load 1 script
    glShaderSource(fragment_shader, 1, (const GLchar**) &fragment_script, 0);

    // Compile fragment shader
    glCompileShader(fragment_shader);


    // Create a "program"
    GLuint program = glCreateProgram();

    // Attach the shaders to that program
    glAttachShader(program, vertex_shader);
    glAttachShader(program, fragment_shader);


    // Link the program (to the GL context I think?)
    glLinkProgram(program);


    // Return the program
    return program;
}


GLuint ccreate_shader1()
{
    return ccreate_shader_program(test1v, test1f);
}


void cuse_program(GLuint program, int param)
{
    glUseProgram(program);

    if (param != 0)
    {
        glUniform1i(
            glGetUniformLocation(program, "paramX"),
            param
        );

        if (param == 5)
        {
            GLfloat blurOffsets[2] = {
                (1.2 / 1024.0),
                0.0
            };

            glUniform2fv(
                glGetUniformLocation(program, "blurOffsets"),
                1,
                blurOffsets
            );
        }

        else if (param == 6)
        {
            GLfloat blurOffsets[2] = {
                0.0,
                (1.2 / 1024.0)
            };

            glUniform2fv(
                glGetUniformLocation(program, "blurOffsets"),
                1,
                blurOffsets
            );
        }
    }
}


GLuint ccreate_framebuffer()
{
    GLuint id = 0;
    glGenFramebuffers(1, &id);

    return id;
}

GLuint cprepare_framebuffer_by_id(int id, int width, int height)
{
    glBindFramebuffer(GL_FRAMEBUFFER, id);

    glLoadIdentity();

if (1) {
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    // this puts us in quadrant 1, rather than quadrant 4
    gluOrtho2D(0, 1024, 1024, 0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
}

    glViewport(0, 0, width, height);
    glLoadIdentity();

    GLuint texture_id = 0;
    glGenTextures(1, &texture_id);

    glBindTexture(GL_TEXTURE_2D, texture_id);

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, 0);

    glBindTexture(GL_TEXTURE_2D, 0);

    // ???
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture_id, 0);

    // ???
    GLenum draw_buffers[2] = { GL_COLOR_ATTACHMENT0 };

    // ???
    glDrawBuffers(1, draw_buffers);


    glBindFramebuffer(GL_FRAMEBUFFER, 0);

if (1) {
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    // this puts us in quadrant 1, rather than quadrant 4
    gluOrtho2D(0, 640, 480, 0);
    glMatrixMode(GL_MODELVIEW);

    glViewport(0, 0, 640, 480);
}

    return texture_id;
}


void cselect_framebuffer(GLuint id)
{
    glBindFramebuffer(GL_FRAMEBUFFER, id);
if (1) {
    if (id > 0) {
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();

    // this puts us in quadrant 1, rather than quadrant 4
    gluOrtho2D(0, 1024, 1024, 0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    }
    else {
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();

    // this puts us in quadrant 1, rather than quadrant 4
    gluOrtho2D(0, 640, 480, 0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    }
}
}
