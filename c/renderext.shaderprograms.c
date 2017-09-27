#define USE_LINUX

#ifdef USE_LINUX
    #include <GL/gl.h>
    #include <GL/glu.h>
#endif

#ifdef USE_CYGWIN
    #include <windows.h>
    #include <w32api/GL/gl.h>
    #include <w32api/GL/glu.h>
    #include <w32api/GL/glext.h>
    #include <w32api/GL/wglext.h>
#endif

#ifdef USE_MINGW
    #include <windows.h>
    #include <GL/gl.h>
    #include <GL/glu.h>
    #include <GL/glext.h>
    #include <GL/wglext.h>
#endif

#define STRINGIFY(A) #A

#include "shaders/vertex.textured.glsl"

#include "shaders/fragment.greyscale.glsl"
#include "shaders/fragment.directionalblur.glsl"


// Create a shader program using a given vertex script and a given fragment script
GLuint ccreate_shader_program(const char *vertex_script, const char *fragment_script)
{
    #ifdef USE_LINUX
    #else
        PFNGLCREATESHADERPROC glCreateShader = (PFNGLCREATESHADERPROC) wglGetProcAddress("glCreateShader");
        PFNGLSHADERSOURCEPROC glShaderSource = (PFNGLSHADERSOURCEPROC) wglGetProcAddress("glShaderSource");
        PFNGLCOMPILESHADERPROC glCompileShader = (PFNGLCOMPILESHADERPROC) wglGetProcAddress("glCompileShader");
        PFNGLCREATEPROGRAMPROC glCreateProgram = (PFNGLCREATEPROGRAMPROC) wglGetProcAddress("glCreateProgram");
        PFNGLLINKPROGRAMPROC glLinkProgram = (PFNGLLINKPROGRAMPROC) wglGetProcAddress("glLinkProgram");
        PFNGLATTACHSHADERPROC glAttachShader = (PFNGLATTACHSHADERPROC) wglGetProcAddress("glAttachShader");

        if (!glCreateShader)
        {
            glCreateShader = (PFNGLCREATESHADERPROC) wglGetProcAddress("glCreateShaderEXT");
        }

        if (!glShaderSource)
        {
            glShaderSource = (PFNGLSHADERSOURCEPROC) wglGetProcAddress("glShaderSourceEXT");
        }

        if (!glCompileShader)
        {
            glCompileShader = (PFNGLCOMPILESHADERPROC) wglGetProcAddress("glCompileShaderEXT");
        }

        if (!glCreateProgram)
        {
            glCreateProgram = (PFNGLCREATEPROGRAMPROC) wglGetProcAddress("glCreateProgramEXT");
        }

        if (!glLinkProgram)
        {
            glLinkProgram = (PFNGLLINKPROGRAMPROC) wglGetProcAddress("glLinkProgramEXT");
        }

        if (!glAttachShader)
        {
            glAttachShader = (PFNGLATTACHSHADERPROC) wglGetProcAddress("glAttachShaderEXT");
        }
    #endif


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


// Create greyscale shader program
GLuint ccreate_greyscale_shader()
{
    return ccreate_shader_program(
        vertexTextured,
        fragmentGreyscale
    );
}


// Create directional blur shader program
GLuint ccreate_directional_blur_shader()
{
    return ccreate_shader_program(
        vertexTextured,
        fragmentDirectionalBlur
    );
}


// Delete a shader program
void cdelete_shader_program(GLuint id)
{
    #ifdef USE_LINUX
    #else
        // Try to get glDeleteProgram
        PFNGLDELETEPROGRAMPROC glDeleteProgram = (PFNGLDELETEPROGRAMPROC) wglGetProcAddress("glDeleteProgram");

        // If we didn't find it, try to get EXT version
        if (!glDeleteProgram)
        {
            glDeleteProgram = (PFNGLDELETEPROGRAMPROC) wglGetProcAddress("glDeleteProgramEXT");
        }
    #endif

    glDeleteProgram(id);
}


// Use a given shader program
void cuse_program(GLuint program)
{
    #ifdef USE_LINUX
    #else
        PFNGLUSEPROGRAMPROC glUseProgram = (PFNGLUSEPROGRAMPROC) wglGetProcAddress("glUseProgram");

        if (!glUseProgram)
        {
            glUseProgram = (PFNGLUSEPROGRAMPROC) wglGetProcAddress("glUseProgramEXT");
        }
    #endif

    glUseProgram(program);
}


// Configure greyscale intensity (0 - 100)
void cconfigure_greyscale_intensity(GLuint program, int percent)
{
    #ifdef USE_LINUX
    #else
        PFNGLUNIFORM1IPROC glUniform1i = (PFNGLUNIFORM1IPROC) wglGetProcAddress("glUniform1i");
        PFNGLGETUNIFORMLOCATIONPROC glGetUniformLocation = (PFNGLGETUNIFORMLOCATIONPROC) wglGetProcAddress("glGetUniformLocation");

        if (!glUniform1i)
        {
            glUniform1i = (PFNGLUNIFORM1IPROC) wglGetProcAddress("glUniform1iEXT");
        }

        if (!glGetUniformLocation)
        {
            glGetUniformLocation = (PFNGLGETUNIFORMLOCATIONPROC) wglGetProcAddress("glGetUniformLocationEXT");
        }
    #endif

    glUniform1i(
        glGetUniformLocation(program, "percent"),
        percent
    );
}


// Configure the directional blur
void cconfigure_directional_blur(GLuint program, int direction, float length)
{
    #ifdef USE_LINUX
    #else
        PFNGLUNIFORM2FVPROC glUniform2fv = (PFNGLUNIFORM2FVPROC) wglGetProcAddress("glUniform2fv");
        PFNGLGETUNIFORMLOCATIONPROC glGetUniformLocation = (PFNGLGETUNIFORMLOCATIONPROC) wglGetProcAddress("glGetUniformLocation");

        if (!glUniform2fv)
        {
            glUniform2fv = (PFNGLUNIFORM2FVPROC) wglGetProcAddress("glUniform2fvEXT");
        }

        if (!glGetUniformLocation)
        {
            glGetUniformLocation = (PFNGLGETUNIFORMLOCATIONPROC) wglGetProcAddress("glGetUniformLocationEXT");
        }
    #endif

    // Horizontal
    if (direction == 0)
    {
        GLfloat blurOffsets[2] = {
            (1.2 / length),
            0.0
        };

        glUniform2fv(
            glGetUniformLocation(program, "blurOffsets"),
            1,
            blurOffsets
        );
    }

    // Vertical
    else if (direction == 1)
    {
        GLfloat blurOffsets[2] = {
            0.0,
            (1.2 / length)
        };

        glUniform2fv(
            glGetUniformLocation(program, "blurOffsets"),
            1,
            blurOffsets
        );
    }
}
