import cv2
import numpy as np



def create_lift_black_lut(
        amount=20
):


    lut = np.arange(
        256,
        dtype=np.float32
    )


    lut = (
        lut *
        (255-amount)
        /
        255
        +
        amount
    )


    lut = np.clip(
        lut,
        0,
        255
    )


    return lut.astype(
        np.uint8
    )




def create_s_curve_lut(
        strength=1.1
):

    lut = np.arange(
        256,
        dtype=np.float32
    )


    lut = (
        lut - 128
    ) * strength + 128


    lut = np.clip(
        lut,
        0,
        255
    )


    return lut.astype(
        np.uint8
    )




def apply_curve(
        image,
        lut
):

    return cv2.LUT(
        image,
        lut
    )
