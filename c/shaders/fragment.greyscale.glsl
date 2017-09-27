const char *fragmentGreyscale = STRINGIFY(

    uniform sampler2D source;

    uniform int percent;

    void main()
    {
        if (percent >= 100)
        {
            gl_FragData[0] = dot(

                texture2D(
                    source,
                    gl_TexCoord[0].st
                ).rgb,

                vec3(0.299, 0.587, 0.114)

            );
        }

        else if (0)
        {
            vec3 rgb = texture2D(source, gl_TexCoord[0].st);
            vec4 rgba = texture2D(source, gl_TexCoord[0].st).rgba;

            float z = ( (100 - percent) / 100.0 );

if (0) {
            gl_FragData[0] = (
                ( percent / 100.0 ) * dot( rgb, vec3(0.299, 0.587, 0.114) ) +
                dot( rgb, vec3(z, z, z) )
            ) / 1.0;
}
                //( (100 - percent) / 100.0 ) * dot( rgb, vec3(1.0, 1.0, 1.0) );

            //gl_FragData[0] = 
              //  ( 1.0 ) * dot( rgb, vec3(0.299, 0.587, 0.114) );

            vec4 asdf = z * rgba;
            asdf.a = rgba.a;
            //asdf = rgba;

            vec3 xyz = z * rgb;
            vec4 xyz2 = (xyz.r, xyz.g, xyz.b, rgba.a);

            //gl_FragData[0] = vec4(rgb.r / 4.0, rgb.g / 4.0, rgb.b / 4.0, 1.0);//rgb;//dot( rgb, vec3(z, z, z) );
            //gl_FragData[0] = asdf;//vec4(asdf.r, asdf.g, asdf.b, 1.0);//rgb;//dot( rgb, vec3(z, z, z) );

            //gl_FragData[0] = ( (xyz2) + ( (1.0 - z) * dot( rgba, vec4(0.299, 0.587, 0.114, 1.0) ) ) ) / 2.0;

            //gl_FragData[0] = (
            //    dot( rgb
        }

        else
        {
            vec4 rgba = texture2D(source, gl_TexCoord[0].st).rgba;

            vec3 greyed = (
                dot( rgba.rgb, vec3(0.299, 0.587, 0.114) ) +
                ( (100 - percent) / 100.0 ) * rgba.rgb
            ) / 2.0;

            gl_FragData[0] = vec4(greyed.r, greyed.g, greyed.b, rgba.a);
        }
    }

);
