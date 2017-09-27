const char *test1f = STRINGIFY(

    uniform sampler2D ct;

    uniform vec2 tcOffset[25];

    uniform float offsetx;
    uniform float zzoffsety;

    uniform vec2 blurOffsets;

    uniform int paramX;

    uniform float mytest;

    void main()
    {
        if (paramX == 1)
        {
            gl_FragData[0] = dot(

                texture2D(
                    ct,
                    gl_TexCoord[0].st
                ).rgb,

                vec3(0.299, 0.587, 0.114)

            );
        }

	    else if (paramX == 2)
	    {
		    vec4 sample[25];

            int i = 0;
		    for (i = 0; i < 25; i++)
		    {
			    // Sample a grid around and including our texel
			    sample[i] = 1;//texture2D(ct, gl_TexCoord[0].st + tcOffset[i]);
		    }
     
		    // Gaussian weighting:
		    // 1  4  6  4 1
		    // 4 16 24 16 4
		    // 6 24 36 24 6 / 256 (i.e. divide by total of weightings)
		    // 4 16 24 16 4
		    // 1  4  6  4 1

    		gl_FragData[0] = (
        	           (1.0  * (sample[0] + sample[4]  + sample[20] + sample[24])) +
                       (4.0  * (sample[1] + sample[3]  + sample[5]  + sample[9] + sample[15] + sample[19] + sample[21] + sample[23])) +
                       (6.0  * (sample[2] + sample[10] + sample[14] + sample[22])) +
                       (16.0 * (sample[6] + sample[8]  + sample[16] + sample[18])) +
                       (24.0 * (sample[7] + sample[11] + sample[13] + sample[17])) +
                       (36.0 * sample[12])
                       ) / 256.0;
	    }

        else if (paramX == 4)
        {
            gl_FragData[0] = vec4(1.0, 0.0, 0.0, 1.0);
        }

        else if (paramX == 3)
        {
            vec4 rgba = texture2D(ct, gl_TexCoord[0].st);

            //if (rgb[0] > rgb[1]) {
            if (rgba.r > rgba.g) {
                gl_FragData[0] = vec4(1.0, 1.0, 0.2, 1.0);
            }
            else {
                gl_FragData[0] = rgba;//vec4(1.0, 1.0, 1.0, 1.0);//texture2D(ct, gl_TexCoord[0].st);//vec4rgb;
            }
        }

        else if (paramX == 5 || paramX == 6)
        {
            vec2 tc = gl_TexCoord[0].st;
            vec2 aoffset = vec2(1.2 / 1024.0, 0.0);//offsetX, zzoffsety);
            vec2 offset = vec2(0.0, 0.0);

            vec2 aoffset5 = vec2(offsetx, zzoffsety);

            if (mytest == 5.5) {
                aoffset5 = vec2(0.0, 0.5);
            }

            //vec2 offset = vec2(0.0
            gl_FragData[0] = (
                (
                    5.0 * texture2D(ct, tc - blurOffsets) +
                    6.0 * texture2D(ct, tc) +
                    5.0 * texture2D(ct, tc + blurOffsets)
                ) / 16.0
            );
        }
    }

);
