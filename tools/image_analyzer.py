"""Deterministic photographic statistics using OpenCV, without external models.

Brightness and contrast use the full-image grayscale histogram (0-255).
Exposure compares the fraction of pixels at <=10 and >=245. HSV statistics
use an INTER_AREA sample with a maximum edge of 1024 pixels; the returned
resolution always describes the original decoded image.

These thresholds are initial heuristics, not camera exposure measurements or
semantic judgments about a scene, subject, lighting direction, or mood.
"""

from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BRIGHTNESS_DARK_LIMIT = 85.0
BRIGHTNESS_BRIGHT_LIMIT = 170.0
CONTRAST_LOW_LIMIT = 30.0
CONTRAST_HIGH_LIMIT = 60.0
SATURATION_LOW_LIMIT = 50.0
SATURATION_HIGH_LIMIT = 150.0
SHADOW_PIXEL_LIMIT = 10
HIGHLIGHT_PIXEL_LIMIT = 245
EXPOSURE_CLIPPED_RATIO = 0.30
EXPOSURE_DOMINANCE_FACTOR = 2.0
DETAIL_CLIPPED_RATIO = 0.05
HSV_MAX_EDGE = 1024
DOMINANT_COLOR_MIN_RATIO = 0.05
DOMINANT_COLOR_LIMIT = 3


def _read_image(image_path: str) -> np.ndarray:
    """Decode an image, including Windows paths containing Unicode."""
    if not isinstance(image_path, str) or not image_path.strip():
        raise ValueError("image_path must be a non-empty string")

    input_path = Path(image_path).expanduser()
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    input_path = input_path.resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Image file not found: {input_path}")
    try:
        image_bytes = np.fromfile(input_path, dtype=np.uint8)
    except OSError as exc:
        raise OSError(f"Unable to read image: {input_path}: {exc}") from exc
    if image_bytes.size == 0:
        raise ValueError(f"Image file is empty: {input_path}")

    try:
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    except cv2.error as exc:
        raise ValueError(f"Unable to decode image: {input_path}") from exc
    if image is None:
        raise ValueError(f"Unable to decode image: {input_path}")
    return image


def _three_level(value: float, low_limit: float, high_limit: float) -> str:
    if value < low_limit:
        return "low"
    if value < high_limit:
        return "medium"
    return "high"


def _hsv_sample(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    longest_edge = max(width, height)
    if longest_edge > HSV_MAX_EDGE:
        scale = HSV_MAX_EDGE / longest_edge
        sample_width = max(1, round(width * scale))
        sample_height = max(1, round(height * scale))
        image = cv2.resize(
            image,
            (sample_width, sample_height),
            interpolation=cv2.INTER_AREA,
        )
    return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)


def _dominant_colors(hsv: np.ndarray) -> list[str]:
    """Return up to three colors ranked by HSV sample pixel coverage.

    OpenCV hue is 0-179. Black has V<40; white has S<30 and V>=200;
    gray has S<30 and 40<=V<200. Remaining pixels use the hue bins below.
    Colors must cover at least 5% of all sampled pixels. Equal counts use
    the listed order, giving repeatable results for uniformly mixed images.
    """
    hue, saturation, value = cv2.split(hsv)
    chromatic = (value >= 40) & (saturation >= 30)
    counts = [
        ("black", int(np.count_nonzero(value < 40))),
        ("white", int(np.count_nonzero((saturation < 30) & (value >= 200)))),
        (
            "gray",
            int(np.count_nonzero((saturation < 30) & (value >= 40) & (value < 200))),
        ),
        ("red", int(np.count_nonzero(chromatic & ((hue < 10) | (hue >= 170))))),
        ("orange", int(np.count_nonzero(chromatic & (hue >= 10) & (hue < 25)))),
        ("yellow", int(np.count_nonzero(chromatic & (hue >= 25) & (hue < 35)))),
        ("green", int(np.count_nonzero(chromatic & (hue >= 35) & (hue < 85)))),
        ("aqua", int(np.count_nonzero(chromatic & (hue >= 85) & (hue < 95)))),
        ("blue", int(np.count_nonzero(chromatic & (hue >= 95) & (hue < 130)))),
        ("purple", int(np.count_nonzero(chromatic & (hue >= 130) & (hue < 150)))),
        ("magenta", int(np.count_nonzero(chromatic & (hue >= 150) & (hue < 170)))),
    ]
    ranked = sorted(counts, key=lambda item: item[1], reverse=True)
    sample_pixels = hsv.shape[0] * hsv.shape[1]
    dominant = [
        name
        for name, count in ranked
        if count / sample_pixels >= DOMINANT_COLOR_MIN_RATIO
    ][:DOMINANT_COLOR_LIMIT]
    return dominant or [ranked[0][0]]


def analyze_image(image_path: str) -> dict[str, Any]:
    """Analyze an image and return JSON-compatible photo analysis fields.

    Relative paths are resolved against the project root. Brightness mean
    <85 is dark and >=170 is bright; grayscale standard deviation <30 is
    low contrast and >=60 is high contrast. Mean HSV saturation <50 is low
    and >=150 is high. Exposure is under/over only when the corresponding
    extreme-pixel ratio is >=30% and at least twice the opposite ratio.
    Technical highlight/shadow conditions separately flag >=5% clipping.

    The six summary fields are also mapped to the existing schema's lighting,
    technical, and color sections. No semantic scene information is inferred.
    """
    image = _read_image(image_path)
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    histogram = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel().astype(np.float64)
    del gray

    pixel_count = float(histogram.sum())
    levels = np.arange(256, dtype=np.float64)
    mean_brightness = float(np.dot(histogram, levels) / pixel_count)
    variance = float(np.dot(histogram, (levels - mean_brightness) ** 2) / pixel_count)
    grayscale_std = float(np.sqrt(max(0.0, variance)))
    highlight_ratio = float(histogram[HIGHLIGHT_PIXEL_LIMIT:].sum() / pixel_count)
    shadow_ratio = float(histogram[:SHADOW_PIXEL_LIMIT + 1].sum() / pixel_count)

    if mean_brightness < BRIGHTNESS_DARK_LIMIT:
        brightness = "dark"
    elif mean_brightness >= BRIGHTNESS_BRIGHT_LIMIT:
        brightness = "bright"
    else:
        brightness = "balanced"
    contrast = _three_level(grayscale_std, CONTRAST_LOW_LIMIT, CONTRAST_HIGH_LIMIT)

    if (
        shadow_ratio >= EXPOSURE_CLIPPED_RATIO
        and shadow_ratio >= EXPOSURE_DOMINANCE_FACTOR * highlight_ratio
    ):
        exposure = "underexposed"
    elif (
        highlight_ratio >= EXPOSURE_CLIPPED_RATIO
        and highlight_ratio >= EXPOSURE_DOMINANCE_FACTOR * shadow_ratio
    ):
        exposure = "overexposed"
    else:
        exposure = "balanced"

    hsv = _hsv_sample(image)
    mean_saturation = float(np.mean(hsv[:, :, 1], dtype=np.float64))
    saturation = _three_level(mean_saturation, SATURATION_LOW_LIMIT, SATURATION_HIGH_LIMIT)
    dominant_colors = _dominant_colors(hsv)

    return {
        "resolution": {"width": int(width), "height": int(height)},
        "brightness": brightness,
        "contrast": contrast,
        "exposure": exposure,
        "saturation": saturation,
        "dominant_colors": dominant_colors,
        "metrics": {
            "mean_brightness": mean_brightness,
            "grayscale_std": grayscale_std,
            "highlight_ratio": highlight_ratio,
            "shadow_ratio": shadow_ratio,
            "mean_saturation": mean_saturation,
            "sample_resolution": {"width": int(hsv.shape[1]), "height": int(hsv.shape[0])},
        },
        "lighting": {"contrast": contrast},
        "technical": {
            "exposure": exposure,
            "highlight_condition": "clipped" if highlight_ratio >= DETAIL_CLIPPED_RATIO else "preserved",
            "shadow_condition": "clipped" if shadow_ratio >= DETAIL_CLIPPED_RATIO else "preserved",
        },
        "color": {"dominant_colors": list(dominant_colors), "saturation": saturation},
    }
