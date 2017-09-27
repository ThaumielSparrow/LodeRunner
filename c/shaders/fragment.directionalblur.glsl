const char *fragmentDirectionalBlur = STRINGIFY(

    uniform sampler2D source;

    uniform vec2 blurOffsets;

    void main()
    {
        vec2 tc = gl_TexCoord[0].st;

        gl_FragData[0] = (
            (
                5.0 * texture2D(source, tc - blurOffsets) +
                6.0 * texture2D(source, tc) +
                5.0 * texture2D(source, tc + blurOffsets)
            ) / 16.0
        );
    }

);
