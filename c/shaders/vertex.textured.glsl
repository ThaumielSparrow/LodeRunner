const char *vertexTextured = STRINGIFY(

    void main()
    {
        // I need this for some reason, to work with textures.  In truth I
        // don't know why, but I don't care too much either.  :)
        gl_TexCoord[0] = gl_MultiTexCoord0;

        // Align the current position or something.
        gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    }

);
