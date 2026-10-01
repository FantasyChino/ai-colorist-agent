import cv2
import numpy as np



# =========================
# Color Range Definition
# =========================


COLOR_RANGES = {


    "red":

    [

        ([0,50,50],[10,255,255]),

        ([170,50,50],[180,255,255])

    ],



    "orange":

    [

        ([10,50,50],[25,255,255])

    ],



    "yellow":

    [

        ([25,50,50],[35,255,255])

    ],



    "green":

    [

        ([35,50,50],[85,255,255])

    ],



    "cyan":

    [

        ([85,50,50],[100,255,255])

    ],



    "blue":

    [

        ([100,50,50],[130,255,255])

    ],



    "purple":

    [

        ([130,50,50],[155,255,255])

    ],



    "magenta":

    [

        ([155,50,50],[170,255,255])

    ]

}




# =========================
# Create Color Mask
# =========================


def create_color_mask(
        hsv,
        color
):


    mask = np.zeros(
        hsv.shape[:2],
        dtype=np.uint8
    )


    ranges = COLOR_RANGES.get(
        color,
        []
    )


    for lower, upper in ranges:


        temp = cv2.inRange(

            hsv,

            np.array(lower),

            np.array(upper)

        )


        mask = cv2.bitwise_or(
            mask,
            temp
        )


    return mask




# =========================
# Adjust HSL
# =========================


def adjust_hsl_region(
        image,
        color,
        hue_shift=0,
        saturation_shift=0,
        brightness_shift=0
):


    # BGR -> HSV
    hsv = cv2.cvtColor(

        image,

        cv2.COLOR_BGR2HSV

    )


    # 转高精度计算
    hsv = hsv.astype(
        np.int16
    )


    # mask需要uint8 HSV
    mask = create_color_mask(

        hsv.astype(
            np.uint8
        ),

        color

    )


    # Hue
    if hue_shift != 0:

        hsv[:,:,0][mask > 0] += hue_shift


        # OpenCV H范围0-179
        hsv[:,:,0][mask > 0] %= 180



    # Saturation

    if saturation_shift != 0:

        hsv[:,:,1][mask > 0] += saturation_shift



    # Brightness(Value)

    if brightness_shift != 0:

        hsv[:,:,2][mask > 0] += brightness_shift



    # =======
    # Clamp
    # =======


    hsv[:,:,0] = np.clip(

        hsv[:,:,0],

        0,

        179

    )


    hsv[:,:,1] = np.clip(

        hsv[:,:,1],

        0,

        255

    )


    hsv[:,:,2] = np.clip(

        hsv[:,:,2],

        0,

        255

    )



    # 转回OpenCV格式

    hsv = hsv.astype(
        np.uint8
    )



    return cv2.cvtColor(

        hsv,

        cv2.COLOR_HSV2BGR

    )





# =========================
# Apply Multiple HSL Rules
# =========================


def apply_hsl_strategy(
        image,
        hsl_strategy
):


    result = image



    for color, params in hsl_strategy.items():


        result = adjust_hsl_region(

            result,

            color,

            params.get(
                "hue",
                0
            ),


            params.get(
                "saturation",
                0
            ),


            params.get(
                "brightness",
                0
            )

        )


    return result


