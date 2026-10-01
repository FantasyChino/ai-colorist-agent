from tools.adjust_color import (
    adjust_brightness,
    adjust_contrast,
    adjust_saturation
)


from tools.tone_curve import (
    create_lift_black_lut,
    create_s_curve_lut,
    apply_curve
)


from tools.hsl_adjustment import (
    apply_hsl_strategy
)


from tools.lut_engine import (
    load_cube,
    apply_simple_lut
)




class ColorPipeline:



    def __init__(self):

        self.history = []



    # ---------------------
    # Basic Correction
    # ---------------------

    def basic_correction(
            self,
            image,
            strategy
    ):


        exposure = strategy.get(
            "exposure",
            0
        )


        if exposure != 0:


            image = adjust_brightness(

                image,

                exposure

            )


            self.history.append(
                "exposure"
            )



        return image




    # ---------------------
    # Tone
    # ---------------------

    def tone_processing(
            self,
            image,
            strategy
    ):


        tone = strategy.get(
            "tone_strategy",
            {}
        )


        contrast = tone.get(
            "contrast"
        )



        if contrast=="low":


            image = adjust_contrast(

                image,

                0.8

            )


        elif contrast=="high":


            image = adjust_contrast(

                image,

                1.2

            )



        if tone.get(
            "black_point"
        )=="lifted":


            lut = create_lift_black_lut(
                20
            )


            image = apply_curve(

                image,

                lut

            )



        self.history.append(
            "tone"
        )


        return image




    # ---------------------
    # HSL
    # ---------------------


    def color_processing(
            self,
            image,
            strategy
    ):


        hsl = strategy.get(
            "hsl_adjustment",
            {}
        )


        if hsl:


            image = apply_hsl_strategy(

                image,

                hsl

            )


            self.history.append(
                "hsl"
            )


        return image




    # ---------------------
    # LUT
    # ---------------------


    def apply_lut(
            self,
            image,
            lut_path
    ):


        lut = load_cube(
            lut_path
        )


        image = apply_simple_lut(

            image,

            lut

        )


        self.history.append(
            "lut"
        )


        return image




    # ---------------------
    # Full Pipeline
    # ---------------------


    def run(
            self,
            image,
            strategy
    ):


        image = self.basic_correction(

            image,

            strategy

        )


        image = self.tone_processing(

            image,

            strategy

        )


        image = self.color_processing(

            image,

            strategy

        )


        if strategy.get(
            "lut"
        ):


            image = self.apply_lut(

                image,

                strategy["lut"]

            )


        return image
