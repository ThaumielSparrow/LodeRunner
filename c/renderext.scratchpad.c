// Linux compilation: (?)
//  gcc -O2 -o renderext.dll -shared -fPIC renderext.scratchpad.c renderext.shaderprograms.c -lGL -lGLU
//    Important to place -lGL and -lGLU at the end, unsure why
//
// Windows compilation:
//  gcc -O2 -shared -o renderext.dll renderext.scratchpad.c renderext.shaderprograms.c -lopengl32 -lglu32

void log(char *s)
{
    if (1)
    {
        printf( s );
        printf( "\n" );
    }
}

#define USE_MINGW

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

#define SCREEN_WIDTH 640
#define SCREEN_HEIGHT 480


const int x = 5;

// Create a scratch pad (frame buffer)
GLuint ccreate_scratch_pad()
{
    // Unique id
    GLuint id = 0;

    // Generate framebuffer for a scratch pad
    #ifdef USE_LINUX
    #else
        // Try to get glGenFramebuffers
        PFNGLGENFRAMEBUFFERSPROC glGenFramebuffers = (PFNGLGENFRAMEBUFFERSPROC) wglGetProcAddress("glGenFramebuffers");

        // If we didn't find it, try to get EXT version
        if (!glGenFramebuffers)
        {
            glGenFramebuffers = (PFNGLGENFRAMEBUFFERSPROC) wglGetProcAddress("glGenFramebuffersEXT");
        }
    #endif

    glGenFramebuffers(1, &id);

    // Return id
    return id;
}


// Delete a scratch pad
void cdelete_scratch_pad(GLuint id)
{
    #ifdef USE_LINUX
    #else
        // Try to get glDeleteFramebuffers
        PFNGLDELETEFRAMEBUFFERSPROC glDeleteFramebuffers = (PFNGLDELETEFRAMEBUFFERSPROC) wglGetProcAddress("glDeleteFramebuffers");

        // If we didn't find it, try to get EXT version
        if (!glDeleteFramebuffers)
        {
            glDeleteFramebuffers = (PFNGLDELETEFRAMEBUFFERSPROC) wglGetProcAddress("glDeleteFramebuffersEXT");
        }
    #endif
        
    glDeleteFramebuffers(1, &id);
}


// Activate a scratch pad
GLuint cactivate_scratch_pad(GLuint id, int width, int height)
{
    BOOL abort = FALSE;

    #ifdef USE_LINUX
    #else
        // Try to get gl extension functions
        PFNGLBINDFRAMEBUFFERPROC glBindFramebuffer = (PFNGLBINDFRAMEBUFFERPROC) wglGetProcAddress("glBindFramebuffer");
        PFNGLFRAMEBUFFERTEXTURE2DPROC glFramebufferTexture2D = (PFNGLFRAMEBUFFERTEXTURE2DPROC) wglGetProcAddress("glFramebufferTexture2D");
        PFNGLDRAWBUFFERSPROC glDrawBuffers = (PFNGLDRAWBUFFERSPROC) wglGetProcAddress("glDrawBuffers");
        //PFNGLBINDTEXTUREEXTPROC glBindTexture = (PFNGLBINDTEXTUREEXTPROC) wglGetProcAddress("glBindTextureEXT");
        ////PFNGLBINDTEXTUREPROC glBindTexture = (PFNGLBINDTEXTUREEXTPROC) wglGetProcAddress("glBindTexture");
        //glBindFramebuffer = NULL;
        //glFramebufferTexture2D = NULL;
        //glDrawBuffers = NULL;
        //glBindTexture = NULL;

        // Try EXT versions
        if (!glBindFramebuffer)
        {
            log( "glBindFrameBuffer does not exist.  Attempting to retrieve EXT version..." );
            glBindFramebuffer = (PFNGLBINDFRAMEBUFFERPROC) wglGetProcAddress("glBindFramebufferEXT");

            if (!glBindFramebuffer) {
                log( "...failed\n");
                abort = TRUE;
            } else {
                log( "\tOK\n");
            }
        } else {
            log( "glBindFramebuffer located successfully" );
        }

        // Try EXT versions
        if (!glFramebufferTexture2D)
        {
            log( "glFramebufferTexture2D does not exist.  Attempting to retrieve EXT version..." );
            //glBindFramebuffer = (PFNGLBINDFRAMEBUFFERPROC) wglGetProcAddress("glFramebufferTexture2DEXT");
            glFramebufferTexture2D = (PFNGLFRAMEBUFFERTEXTURE2DPROC) wglGetProcAddress("glFramebufferTexture2DEXT");

            if (!glFramebufferTexture2D) {
                log( "...failed\n");
                abort = TRUE;
            } else {
                log( "\tOK\n");
            }
        } else {
            log( "glFramebufferTexture2D located successfully" );
        }

        // Try EXT versions
        if (!glDrawBuffers)
        {
            log( "glDrawBuffers does not exist.  Attempting to retrieve EXT version..." );
            //glBindFramebuffer = (PFNGLBINDFRAMEBUFFERPROC) wglGetProcAddress("glDrawBuffersEXT");
            glDrawBuffers = (PFNGLDRAWBUFFERSPROC) wglGetProcAddress("glDrawBuffersEXT");

            if (!glDrawBuffers) {
                log( "...failed\n");
                abort = TRUE;
            } else {
                log( "\tOK\n");
            }
        } else {
            log( "glDrawBuffers located successfully" );
        }

        // Try EXT versions
        #ifdef DISABLED
        if (!glBindTexture)
        {
            log( "glBindTexture does not exist.  Attempting to retrieve EXT version..." );
            glBindTexture = (PFNGLBINDTEXTUREEXTPROC) wglGetProcAddress("glBindTextureEXT");

            if (!glBindTexture) {
                log( "...failed\n");
                abort = TRUE;
            } else {
                log( "\tOK\n");
            }
        } else {
            log( "glBindTexture located successfully" );
        }
        #endif
    #endif

    if (abort) {
        return -1;
    }
    
    // Focus on the given scratch pad
    glBindFramebuffer(GL_FRAMEBUFFER, id);


    // Switch to projection matrix
    glMatrixMode(GL_PROJECTION);

    // Reset, then configure to render to the dimensions of the scratch pad
    glLoadIdentity();
    gluOrtho2D(0, width, height, 0);     // this puts us in quadrant 1, rather than quadrant 4

    // Back to model/view matrix
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    // Use the entire scratchpad size as a viewport
    glViewport(0, 0, width, height);


    // Create the texture we'll render to
    GLuint texture_id = 0;
    glGenTextures(1, &texture_id);

    // Bind texture
    glBindTexture(GL_TEXTURE_2D, texture_id);

    // Params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);

    // Generate
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, 0);

    // ???
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture_id, 0);

    // ???
    GLenum draw_buffers[2] = { GL_COLOR_ATTACHMENT0 };

    // ???
    glDrawBuffers(1, draw_buffers);


    // Back to default framebuffer
    glBindFramebuffer(GL_FRAMEBUFFER, 0);


    // we need to go back and set the project to use the app's width/height and all that
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();

    gluOrtho2D(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0);    // this puts us in quadrant 1, rather than quadrant 4

    glMatrixMode(GL_MODELVIEW);
    glViewport(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);


    // Return the id of the texture we created for this scratch pad
    return texture_id;
}


// Render to a given scratch pad
void crender_to_scratch_pad(GLuint id, int width, int height)
{
    #ifdef USE_LINUX
    #else
        // Try to get glGenFramebuffers
        PFNGLBINDFRAMEBUFFERPROC glBindFramebuffer = (PFNGLBINDFRAMEBUFFERPROC) wglGetProcAddress("glBindFramebuffer");

        // If we didn't find it, try to get EXT version
        if (!glBindFramebuffer)
        {
            glBindFramebuffer = (PFNGLBINDFRAMEBUFFERPROC) wglGetProcAddress("glBindFramebufferEXT");
        }
    #endif

    // Bind the given pad (or 0 for default framebuffer)
    glBindFramebuffer(GL_FRAMEBUFFER, id);

    // If we're on a given scratch pad...
    if (id > 0)
    {
        // Update projection matrix to use entire scratch pad
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();

        gluOrtho2D(0, width, height, 0);    // this puts us in quadrant 1, rather than quadrant 4

        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        glViewport(0, 0, width, height);

        glReadBuffer(GL_COLOR_ATTACHMENT0);
    }

    // If we're on the default framebuffer, configure the projection matrix for the app's resolution
    else
    {
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();

        gluOrtho2D(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0);    // this puts us in quadrant 1, rather than quadrant 4

        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        glViewport(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);

        glReadBuffer(GL_BACK);
    }
}
