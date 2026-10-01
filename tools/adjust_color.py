import cv2
import numpy as np



def adjust_brightness(
        image,
        value
):

    img = image.astype(
        np.float32
    )


    img += value


    img = np.clip(
        img,
        0,
        255
    )


    return img.astype(
        np.uint8
    )




def adjust_contrast(
        image,
        factor
):


    img = image.astype(
        np.float32
    )


    img = (
        img - 128
    ) * factor + 128


    img = np.clip(
        img,
        0,
        255
    )


    return img.astype(
        np.uint8
    )




def adjust_saturation(
        image,
        value
):


    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )


    hsv[:,:,1] = np.clip(

        hsv[:,:,1] + value,

        0,

        255

    )


    return cv2.cvtColor(

        hsv,

        cv2.COLOR_HSV2BGR

    )




def lift_black(
        image,
        amount
):


    img = image.astype(
        np.float32
    )


    img += amount


    img = np.clip(
        img,
        0,
        255
    )


    return img.astype(
        np.uint8
    )
