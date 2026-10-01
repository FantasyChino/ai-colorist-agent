"""Fit a source-dependent global creative LUT from unpaired photographic works.

This is statistical distribution fitting, not neural-network training or recovery
of a photographer's original editing curve. Content and illumination remain
confounded with style. Only OpenCV and NumPy are required; existing grading tools
are not changed. The function writes a CUBE/profile, never an output photograph.

Method context:
https://mural.maynoothuniversity.ie/id/eprint/15125/
https://docs.opencv.org/4.x/d8/d01/group__imgproc__color__conversions.html
"""

from pathlib import Path
import hashlib
import json
import math
import os
import re
import tempfile

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METHOD = "unpaired_source_matched_creative_lab_fit_v6"
IMPLEMENTATION_VERSION = "2026-10-01.5"
MIN_REFERENCES = 500
MAX_CANDIDATES = 10_000
LUT_SIZE = 33
LUMA_BINS = 8
QUANTILES = np.linspace(0.01, 0.99, 99)
MAX_EDGE = 512
MAX_SAMPLES = 8192
MAX_FILE_BYTES = 32 * 1024 * 1024
TONE_IDENTITY_PRIOR = 0.55
TONE_SLOPE_MIN = 0.82
TONE_SLOPE_MAX = 1.35


class ReferenceSetError(ValueError):
    """Expose actual accepted/rejected counts to an MCP wrapper on failure."""

    def __init__(self, details):
        self.details = details
        super().__init__(
            f"At least {MIN_REFERENCES} unique decodable reference images are required; "
            f"accepted={details['accepted']}, candidates={details['candidates']}, "
            f"rejected={details['rejected']}; rejects={details['reject_summary']}"
        )


def _resolve(path):
    path = Path(path)
    return (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _slug(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("style_name must be a nonempty string")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-_").lower()[:56]
    if not slug:
        slug = "style-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
    if slug.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        slug = "style-" + slug
    return slug


def _read_sample(path):
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file_larger_than_32_MiB")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    flags = cv2.IMREAD_REDUCED_COLOR_4 if path.suffix.lower() in {".jpg", ".jpeg"} else cv2.IMREAD_COLOR
    image = cv2.imdecode(np.frombuffer(data, np.uint8), flags)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("not_a_decodable_color_image")
    if image.shape[0] * image.shape[1] < 64:
        raise ValueError("fewer_than_64_decoded_pixels")
    factor = min(1, MAX_EDGE / max(image.shape[:2]))
    width = max(1, round(image.shape[1] * factor))
    height = max(1, round(image.shape[0] * factor))
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    pixel_digest = hashlib.sha256(str(image.shape).encode("ascii") + image.tobytes()).hexdigest()
    return image, digest, pixel_digest


def _mean_cov(ab):
    # Winsorization prevents a few bright colored pixels from dominating a bin.
    low, high = np.quantile(ab, [0.01, 0.99], axis=0)
    bounded = np.clip(ab, low, high)
    mean = bounded.mean(axis=0)
    centered = bounded - mean
    covariance = centered.T @ centered / max(1, len(bounded))
    return mean, covariance


def _image_statistics(image):
    lab = cv2.cvtColor(image.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab).reshape(-1, 3)
    if len(lab) > MAX_SAMPLES:
        lab = lab[np.linspace(0, len(lab) - 1, MAX_SAMPLES, dtype=np.int64)]
    lab = lab.astype(np.float64)
    luminance, ab = lab[:, 0], lab[:, 1:]
    cuts = np.quantile(luminance, np.arange(1, LUMA_BINS) / LUMA_BINS)
    membership = np.searchsorted(cuts, luminance, side="right")
    global_mean, global_covariance = _mean_cov(ab)
    means, covariances, counts = [], [], []
    for index in range(LUMA_BINS):
        values = ab[membership == index]
        counts.append(len(values))
        mean, covariance = _mean_cov(values) if len(values) >= 8 else (global_mean, global_covariance)
        means.append(mean)
        covariances.append(covariance)
    chroma = np.linalg.norm(ab, axis=1)
    luma_quantiles = np.quantile(luminance, QUANTILES)
    luma_span = float(luma_quantiles[-1] - luma_quantiles[0])
    normalized_luma_quantiles = (
        (luma_quantiles - luma_quantiles[0]) * (100.0 / luma_span)
        if luma_span > 1e-6
        else np.full_like(luma_quantiles, 50.0)
    )
    return {
        "luma_quantiles": luma_quantiles,
        "normalized_luma_quantiles": normalized_luma_quantiles,
        "ab_means": np.asarray(means),
        "ab_covariances": np.asarray(covariances),
        "bin_sample_counts": np.asarray(counts),
        "mean_chroma": float(chroma.mean()),
        "color_like": bool(np.mean(chroma > 3.0) > 0.10),
        "sample_count": len(lab),
    }


def _selection_feature(stats):
    quantile_indices = np.linspace(0, len(QUANTILES) - 1, 9, dtype=np.int64)
    return np.concatenate(
        (
            0.4 * stats["normalized_luma_quantiles"][quantile_indices] / 25.0,
            stats["ab_means"].reshape(-1) / 12.0,
            [stats["mean_chroma"] / 10.0],
        )
    )


def _select_creative_mode(statistics, source_stats):
    """Select a source-compatible, high-color mode after modeling the full corpus."""
    corpus_color_ratio = float(np.mean([item["color_like"] for item in statistics]))
    monochrome_dominant = corpus_color_ratio <= 0.50
    if monochrome_dominant:
        quantile_indices = np.linspace(0, len(QUANTILES) - 1, 17, dtype=np.int64)
        features = np.stack(
            [item["normalized_luma_quantiles"][quantile_indices] / 25.0 for item in statistics]
        )
        source_feature = source_stats["normalized_luma_quantiles"][quantile_indices] / 25.0
    else:
        features = np.stack([_selection_feature(item) for item in statistics])
        source_feature = _selection_feature(source_stats)
    distances = np.linalg.norm(features - source_feature, axis=1)
    pool_count = max(100, round(len(statistics) * 0.40))
    selected_count = max(50, round(len(statistics) * 0.10))
    pool_count = min(pool_count, len(statistics))
    selected_count = min(selected_count, pool_count)
    compatible = np.argsort(distances, kind="stable")[:pool_count]
    # A predominantly monochrome portfolio should remain monochrome rather than
    # letting a few colored outliers win. Color-dominant portfolios prefer the
    # stronger finished-color examples inside a broad compatible pool; this
    # avoids the gray average from unrelated subject palettes.
    ranked = sorted(
        compatible.tolist(),
        key=(
            (lambda index: (statistics[index]["mean_chroma"], distances[index], index))
            if monochrome_dominant
            else (lambda index: (-statistics[index]["mean_chroma"], distances[index], index))
        ),
    )
    selected = np.asarray(ranked[:selected_count], dtype=np.int64)
    return selected, {
        "method": (
            "monochrome_dominant_tone_compatible_pool_then_lowest_chroma_10_percent"
            if monochrome_dominant
            else "color_dominant_source_compatible_pool_then_highest_chroma_10_percent"
        ),
        "corpus_color_image_ratio": corpus_color_ratio,
        "corpus_count": len(statistics),
        "compatible_pool_count": pool_count,
        "selected_count": selected_count,
        "selected_distance_mean": float(np.mean(distances[selected])),
        "corpus_distance_median": float(np.median(distances)),
    }


def _reference_profile(directory, source_digest, source_pixel_digest, source_stats):
    paths = sorted(
        (path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}),
        key=lambda path: str(path).casefold(),
    )
    if len(paths) > MAX_CANDIDATES:
        raise ValueError(
            f"reference_dir contains {len(paths)} candidate images; maximum is {MAX_CANDIDATES}. "
            "Use a curated reference directory or collection manifest."
        )
    statistics, accepted, rejected = [], [], []
    seen_hashes, seen_pixels = set(), set()
    for path in paths:
        try:
            image, digest, pixel_digest = _read_sample(path)
            if digest == source_digest or pixel_digest == source_pixel_digest:
                reason = "reference_matches_source_image"
            elif digest in seen_hashes:
                reason = "duplicate_file_sha256"
            elif pixel_digest in seen_pixels:
                reason = "duplicate_decoded_thumbnail_sha256"
            else:
                reason = None
            if reason:
                rejected.append({"path": str(path.resolve()), "reason": reason, "sha256": digest})
                continue
            seen_hashes.add(digest)
            seen_pixels.add(pixel_digest)
            stats = _image_statistics(image)
            statistics.append(stats)
            accepted.append({
                "path": str(path.resolve()), "sha256": digest,
                "decoded_thumbnail_sha256": pixel_digest,
                "sample_count": stats["sample_count"], "color_like": stats["color_like"],
            })
        except (OSError, ValueError, cv2.error) as exc:
            rejected.append({"path": str(path.resolve()), "reason": str(exc)})
    reject_summary = {}
    for item in rejected:
        reason = item["reason"]
        reject_summary[reason] = reject_summary.get(reason, 0) + 1
    counts = {"candidates": len(paths), "accepted": len(accepted), "rejected": len(rejected), "reject_summary": reject_summary}
    if len(accepted) < MIN_REFERENCES:
        raise ReferenceSetError({**counts, "rejects": rejected})
    selected_indices, selection = _select_creative_mode(statistics, source_stats)
    selected_statistics = [statistics[index] for index in selected_indices]
    target = {
        "luma_quantiles": np.median(
            np.stack([item["luma_quantiles"] for item in selected_statistics]), axis=0
        ),
        "normalized_luma_quantiles": np.median(
            np.stack([item["normalized_luma_quantiles"] for item in selected_statistics]), axis=0
        ),
        "ab_means": np.median(
            np.stack([item["ab_means"] for item in selected_statistics]), axis=0
        ),
        "ab_covariances": np.median(
            np.stack([item["ab_covariances"] for item in selected_statistics]), axis=0
        ),
        "color_image_ratio": float(np.mean([item["color_like"] for item in selected_statistics])),
        "corpus_color_image_ratio": float(np.mean([item["color_like"] for item in statistics])),
        "mean_chroma_median": float(
            np.median([item["mean_chroma"] for item in selected_statistics])
        ),
        "corpus_mean_chroma_median": float(np.median([item["mean_chroma"] for item in statistics])),
        "selection": {
            **selection,
            "selected_reference_sha256": [accepted[index]["sha256"] for index in selected_indices],
        },
    }
    target["monochrome_like"] = target["color_image_ratio"] <= 0.05
    counts["color_like_images"] = sum(item["color_like"] for item in statistics)
    counts["monochrome_like_images"] = len(statistics) - counts["color_like_images"]
    fingerprint = hashlib.sha256("\n".join(sorted(seen_hashes)).encode("ascii")).hexdigest()
    return target, accepted, rejected, counts, fingerprint


def _psd(matrix, minimum=1.0):
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2)
    return (vectors * np.maximum(values, minimum)) @ vectors.T


def _matrix_power(matrix, power):
    values, vectors = np.linalg.eigh(_psd(matrix))
    return (vectors * values ** power) @ vectors.T


def _tone_curve(source_quantiles, target_quantiles, identity_anchors=()):
    # Collapse repeated source quantiles instead of interpolating ambiguous knots.
    unique, inverse = np.unique(source_quantiles, return_inverse=True)
    totals = np.bincount(inverse, weights=target_quantiles)
    counts = np.bincount(inverse)
    values = totals / counts
    interior = (unique > 0) & (unique < 100)
    knots = np.concatenate(([0.0], unique[interior], [100.0]))
    targets = np.concatenate(([0.0], values[interior], [100.0]))
    anchors = np.asarray(
        sorted({float(value) for value in identity_anchors if 0 < float(value) < 100}),
        dtype=np.float64,
    )
    axis = np.unique(np.concatenate((np.linspace(0, 100, 257), anchors)))
    fitted = np.interp(axis, knots, targets)
    fitted = TONE_IDENTITY_PRIOR * axis + (1 - TONE_IDENTITY_PRIOR) * fitted
    # Project each identity-anchored interval onto bounded slopes while keeping
    # the interval's endpoint sum fixed. This preserves the source's 1st/99th
    # percentile anchors and still keeps strength<=2 extrapolation monotone.
    increments = np.diff(fitted)
    widths = np.diff(axis)
    boundary_indices = [0, *[int(np.searchsorted(axis, value)) for value in anchors], len(axis) - 1]
    for start, stop in zip(boundary_indices, boundary_indices[1:]):
        segment = increments[start:stop]
        segment_widths = widths[start:stop]
        target_sum = axis[stop] - axis[start]
        left, right = -100.0, 100.0
        for _ in range(64):
            middle = (left + right) / 2
            projected = np.clip(
                segment + middle * segment_widths,
                TONE_SLOPE_MIN * segment_widths,
                TONE_SLOPE_MAX * segment_widths,
            )
            if projected.sum() < target_sum:
                left = middle
            else:
                right = middle
        increments[start:stop] = np.clip(
            segment + ((left + right) / 2) * segment_widths,
            TONE_SLOPE_MIN * segment_widths,
            TONE_SLOPE_MAX * segment_widths,
        )
    return axis, np.concatenate(([0.0], np.cumsum(increments)))


def _fit_mapping(source, target):
    source_low, source_high = source["luma_quantiles"][[0, -1]]
    source_span = max(float(source_high - source_low), 1e-6)
    # Absolute brightness is dominated by subject and capture conditions. Learn
    # the corpus's within-image tonal shape while anchoring this source's 1st and
    # 99th percentiles, so a bright-sky/dark-foreground scene is not flattened
    # merely because the portfolio median has a narrower absolute histogram.
    shaped_target = source_low + target["normalized_luma_quantiles"] * (source_span / 100.0)
    axis, curve = _tone_curve(
        source["luma_quantiles"], shaped_target, identity_anchors=(source_low, source_high)
    )
    transforms, offsets = [], []
    for index in range(LUMA_BINS):
        source_covariance = _psd(source["ab_covariances"][index])
        target_covariance = _psd(target["ab_covariances"][index])
        # Symmetric Gaussian transport, regularized away from unstable tiny bins.
        half = _matrix_power(source_covariance, 0.5)
        inverse_half = _matrix_power(source_covariance, -0.5)
        transport = inverse_half @ _matrix_power(half @ target_covariance @ half, 0.5) @ inverse_half
        values, vectors = np.linalg.eigh((transport + transport.T) / 2)
        transport = (vectors * np.clip(values, 0.55, 1.45)) @ vectors.T
        transport = 0.20 * np.eye(2) + 0.80 * transport
        offset = target["ab_means"][index] - transport @ source["ab_means"][index]
        transforms.append(transport)
        offsets.append(np.clip(offset, -18, 18) * 0.80)
    rank_axis, rank_values = _collapse_quantile_ranks(source["luma_quantiles"])
    return {
        "luma_axis": axis, "luma_curve": curve,
        "source_luma_quantiles": source["luma_quantiles"],
        "source_tone_anchor_lstar": [float(source_low), float(source_high)],
        "target_tone_shape_quantiles": target["normalized_luma_quantiles"],
        "rank_luma_axis": rank_axis, "rank_values": rank_values,
        "ab_transforms": np.asarray(transforms), "ab_offsets": np.asarray(offsets),
        "monochrome_like": target["monochrome_like"],
        "creative_chroma_floor_ratio": (
            1.0
            if target["monochrome_like"]
            else float(
                np.clip(
                    target["mean_chroma_median"] / max(source["mean_chroma"], 1e-6),
                    1.0,
                    1.35,
                )
            )
        ),
    }


def _collapse_quantile_ranks(luma_quantiles):
    """Merge repeated luminance knots before interpolation.

    Flat and quantized source photographs can repeat the same L* at many
    percentiles. Using duplicate x coordinates directly in np.interp creates a
    discontinuous jump from the first to the last rank at that luminance.
    """
    unique, inverse = np.unique(np.asarray(luma_quantiles, dtype=np.float64), return_inverse=True)
    totals = np.bincount(inverse, weights=QUANTILES)
    counts = np.bincount(inverse)
    return unique, totals / counts


def _lab_to_linear_rgb(lab):
    fy = (lab[:, 0] + 16) / 116
    xyz = np.column_stack((fy + lab[:, 1] / 500, fy, fy - lab[:, 2] / 200))
    delta = 6 / 29
    xyz = np.where(xyz > delta, xyz ** 3, 3 * delta ** 2 * (xyz - 4 / 29))
    xyz *= np.array([0.950456, 1.0, 1.088754])
    matrix = np.array([[3.240479, -1.537150, -0.498535], [-0.969256, 1.875991, 0.041556], [0.055648, -0.204043, 1.057311]])
    return xyz @ matrix.T


def _gamut_compress(lab):
    linear = _lab_to_linear_rgb(lab)
    outside = np.any((linear < -1e-6) | (linear > 1 + 1e-6), axis=1)
    if np.any(outside):
        values = lab[outside].copy()
        original_ab = values[:, 1:].copy()
        low, high = np.zeros(len(values)), np.ones(len(values))
        for _ in range(16):
            factor = (low + high) / 2
            values[:, 1:] = original_ab * factor[:, None]
            candidate = _lab_to_linear_rgb(values)
            valid = np.all((candidate >= -1e-6) & (candidate <= 1 + 1e-6), axis=1)
            low = np.where(valid, factor, low)
            high = np.where(valid, high, factor)
        values[:, 1:] = original_ab * low[:, None]
        linear[outside] = _lab_to_linear_rgb(values)
    clipped = np.clip(linear, 0, 1)
    rgb = np.where(clipped <= 0.0031308, 12.92 * clipped, 1.055 * clipped ** (1 / 2.4) - 0.055)
    return rgb, float(outside.mean())


def _bake_lut(mapping, strength):
    blue, green, red = np.indices((LUT_SIZE,) * 3, dtype=np.float32)
    rgb = np.stack((red, green, blue), axis=-1).reshape(-1, 3) / (LUT_SIZE - 1)
    if strength == 0:
        return rgb.astype(np.float64), {"compressed_node_fraction": 0.0}
    lab = cv2.cvtColor(rgb.reshape(1, -1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3).astype(np.float64)
    original_l = lab[:, 0].copy()
    fitted_l = np.interp(original_l, mapping["luma_axis"], mapping["luma_curve"])
    lab[:, 0] = np.clip(original_l + strength * (fitted_l - original_l), 0, 100)
    # Source-relative luminance ranks align shadow/midtone/highlight palettes.
    ranks = np.interp(original_l, mapping["rank_luma_axis"], mapping["rank_values"])
    centers = (np.arange(LUMA_BINS) + 0.5) / LUMA_BINS
    matrices = np.empty((len(lab), 2, 2))
    offsets = np.empty((len(lab), 2))
    for row in range(2):
        offsets[:, row] = np.interp(ranks, centers, mapping["ab_offsets"][:, row])
        for column in range(2):
            matrices[:, row, column] = np.interp(ranks, centers, mapping["ab_transforms"][:, row, column])
    transformed_ab = np.einsum("nij,nj->ni", matrices, lab[:, 1:]) + offsets
    endpoint_guard = np.sin(np.pi * np.clip(original_l, 0, 100) / 100) ** 0.6
    if mapping["monochrome_like"]:
        # All references still count; nearly all-achromatic data selects this fit.
        lab[:, 1:] *= max(0.0, 1 - min(strength, 1.0))
    else:
        original_ab = lab[:, 1:].copy()
        graded_ab = original_ab + strength * endpoint_guard[:, None] * (transformed_ab - original_ab)
        original_chroma = np.linalg.norm(original_ab, axis=1)
        graded_chroma = np.linalg.norm(graded_ab, axis=1)
        floor_ratio = 1 + endpoint_guard * min(strength, 1.5) * (
            mapping["creative_chroma_floor_ratio"] - 1
        )
        minimum_chroma = original_chroma * floor_ratio
        needs_floor = (original_chroma > 1e-6) & (graded_chroma < minimum_chroma)
        graded_ab[needs_floor] *= (
            minimum_chroma[needs_floor] / np.maximum(graded_chroma[needs_floor], 1e-6)
        )[:, None]
        lab[:, 1:] = graded_ab
    table, fraction = _gamut_compress(lab)
    table[0], table[-1] = 0, 1
    return table, {"compressed_node_fraction": fraction}


def _sample_cube(table, rgb):
    coordinates = np.asarray(rgb, dtype=np.float64) * (LUT_SIZE - 1)
    lower = np.floor(coordinates).astype(np.int64)
    upper = np.minimum(lower + 1, LUT_SIZE - 1)
    fractions = coordinates - lower
    result = np.zeros_like(coordinates)
    for rbit in (0, 1):
        for gbit in (0, 1):
            for bbit in (0, 1):
                indices = [upper[:, c] if bit else lower[:, c] for c, bit in enumerate((rbit, gbit, bbit))]
                weight = np.ones(len(rgb))
                for channel, bit in enumerate((rbit, gbit, bbit)):
                    weight *= fractions[:, channel] if bit else 1 - fractions[:, channel]
                result += table[indices[0] + LUT_SIZE * indices[1] + LUT_SIZE ** 2 * indices[2]] * weight[:, None]
    return result


def _quality_control(table, gamut):
    ramp = np.repeat(np.linspace(0, 1, 1025)[:, None], 3, axis=1)
    mapped = _sample_cube(table, ramp)
    lab = cv2.cvtColor(mapped.astype(np.float32).reshape(1, -1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    steps = np.diff(lab[:, 0])
    grid = table.reshape(LUT_SIZE, LUT_SIZE, LUT_SIZE, 3)
    curvature = max(float(np.max(np.abs(np.diff(grid, n=2, axis=axis)))) for axis in range(3))
    valid = bool(table.shape == (LUT_SIZE ** 3, 3) and np.isfinite(table).all() and table.min() >= 0 and table.max() <= 1)
    return {
        "valid_cube": valid, "size": LUT_SIZE, "rows": len(table), "red_fastest": True,
        "black_rgb": table[0].tolist(), "white_rgb": table[-1].tolist(),
        "neutral_ramp_lstar_decreasing_steps_over_0_025": int(np.count_nonzero(steps < -0.025)),
        "neutral_ramp_min_lstar_step": float(steps.min()),
        "max_lattice_second_difference": curvature,
        "gamut": gamut,
        "notes": ["OpenCV float Lab conversion has small numeric quantization; QC uses a 0.025 L* decrease tolerance.", "Lattice/gamut/neutral-ramp statistics are diagnostics, not aesthetic quality scores or semantic skin protection."],
    }


def _guard_write_plan(paths, inputs):
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
            raise ValueError("Learned outputs must remain within the project")
        for source in inputs:
            if resolved == source.resolve() or (path.exists() and source.exists() and path.samefile(source)):
                raise ValueError("A learned output would overwrite a source/reference image")


def _atomic_text_write(path, writer):
    """Write a text artifact completely, then atomically replace its target."""
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            writer(stream)
        os.replace(temporary_path, path)
    except BaseException:
        try:
            temporary_path.unlink(missing_ok=True)
        finally:
            raise


def _atomic_write_string(path, value):
    _atomic_text_write(path, lambda stream: stream.write(value))


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def learn_style_lut(source_image_path, reference_dir, style_name, strength=1.0):
    """Fit from at least 500 unique images; return a source-dependent CUBE/profile.

    strength is finite in [0,2]. Values above 1 extrapolate this constrained fit;
    they do not reveal an author's original edits. Every reference, including
    black-and-white work, receives one vote during source-compatible mode
    selection; the selected mode supplies the robust target. The source is never
    modified.
    """
    if not isinstance(strength, (int, float)) or not math.isfinite(strength) or not 0 <= strength <= 2:
        raise ValueError("strength must be a finite number between 0 and 2")
    slug = _slug(style_name)
    source, directory = _resolve(source_image_path), _resolve(reference_dir)
    if not source.is_file() or not directory.is_dir():
        raise ValueError("source_image_path must be a file and reference_dir must be a directory")
    sample, source_digest, source_pixels = _read_sample(source)
    source_stats = _image_statistics(sample)
    target, accepted, rejected, counts, fingerprint = _reference_profile(
        directory, source_digest, source_pixels, source_stats
    )
    mapping = _fit_mapping(source_stats, target)
    table, gamut = _bake_lut(mapping, float(strength))
    qc = _quality_control(table, gamut)
    if not qc["valid_cube"] or qc["neutral_ramp_lstar_decreasing_steps_over_0_025"]:
        raise ValueError("Learned LUT failed numeric/neutral-ramp QC; no output was written")
    run_identity = json.dumps(
        {
            "implementation_version": IMPLEMENTATION_VERSION,
            "method": METHOD,
            "source_sha256": source_digest,
            "reference_corpus_sha256": fingerprint,
            "strength": f"{strength:.12g}",
            "style_name": style_name,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    run_hash = hashlib.sha256(run_identity).hexdigest()[:12]
    output_dir = (PROJECT_ROOT / "assets/luts/learned" / slug).resolve()
    prefix = output_dir / f"fit-{run_hash}"
    cube_path = prefix.with_suffix(".cube")
    profile_path = prefix.with_suffix(".profile.json")
    manifest_path = prefix.with_suffix(".manifest.json")
    _guard_write_plan([cube_path, profile_path, manifest_path], [source, *[Path(item["path"]) for item in accepted]])
    output_dir.mkdir(parents=True, exist_ok=True)
    creative_mode_warning = (
        "The creative target is the lowest-chroma tone-compatible mode selected after analyzing the full corpus; it is not the photographer's single canonical look."
        if target["monochrome_like"]
        else "The creative target is the strongest-color source-compatible mode selected after analyzing the full corpus; it is not the photographer's single canonical look."
    )
    warnings = [
        "Nonpaired photographs identify a reference color distribution, not the photographer's original scene-to-grade curve.",
        "Palette statistics mix subject content, illumination, camera rendering and editing; this LUT is conditioned on this source photograph.",
        creative_mode_warning,
        "Encoded sRGB JPEG/PNG is assumed. OpenCV performs no ICC-profile, RAW, camera Log, HDR or P3 interpretation.",
        "Fixed identity, slope, endpoint, chroma and gamut constraints are declared guardrails, not learned author decisions.",
        "A global LUT has no spatial masks, object understanding, grain, halation or recovery of clipped source information.",
    ]
    if strength > 1:
        warnings.append("strength>1 extrapolates the statistical approximation; it is not evidence of accurate author-style reconstruction.")
    if 0.05 < target["color_image_ratio"] < 0.95:
        warnings.append("The selected creative mode mixes color-like and monochrome-like photographs, so its robust target can average distinct treatments.")
    def write_cube(stream):
        stream.write(f'# Statistical unpaired style approximation: {style_name.replace(chr(10), " ").replace(chr(13), " ")}\n')
        stream.write(f'# Method: {METHOD}; implementation={IMPLEMENTATION_VERSION}; source-dependent; strength={strength:.12g}\n')
        stream.write(f'# Accepted references: {counts["accepted"]}; corpus SHA256: {fingerprint}\n')
        stream.write('# Encoded sRGB assumption; no claim of original author LUT or image-content transformation.\n')
        stream.write(f'TITLE "learned-{slug}"\nLUT_3D_SIZE {LUT_SIZE}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(stream, table, fmt="%.9f")
    _atomic_text_write(cube_path, write_cube)
    manifest = {
        "method": METHOD, "reference_directory": str(directory), "counts": counts,
        "reference_corpus_sha256": fingerprint, "accepted": accepted, "rejected": rejected,
        "uniqueness": "Encoded-file SHA256 plus exact decoded thumbnail SHA256; near-duplicates are not reliably identified.",
        "rights": "Reference files remain at their source paths. This function does not infer a license from a photographer name or redistribute reference photographs.",
    }
    collection_root = directory.parent if directory.name.casefold() == "images" else directory
    upstream_records = {}
    for filename in ("manifest.json", "validation.json", "verification.json", "icc-audit.json"):
        upstream_path = collection_root / filename
        if upstream_path.is_file():
            upstream_records[filename] = {
                "path": str(upstream_path.resolve()),
                "sha256": hashlib.sha256(upstream_path.read_bytes()).hexdigest(),
            }
    if upstream_records:
        manifest["upstream_collection_records"] = upstream_records
    _atomic_write_string(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    profile = {
        "method": METHOD, "implementation_version": IMPLEMENTATION_VERSION,
        "runtime_versions": {"opencv": cv2.__version__, "numpy": np.__version__},
        "style_name": style_name, "source_dependent": True,
        "source": {"path": str(source), "sha256": source_digest, "decoded_thumbnail_sha256": source_pixels},
        "reference_count": counts["accepted"],
        "selected_reference_count": target["selection"]["selected_count"],
        "counts": counts, "strength": float(strength),
        "target_statistics": _jsonable(target), "source_statistics": _jsonable(source_stats), "fitted_mapping": _jsonable(mapping),
        "guardrails": {"tone_identity_prior": TONE_IDENTITY_PRIOR, "tone_slope_range": [TONE_SLOPE_MIN, TONE_SLOPE_MAX], "black_white_lstar": [0, 100], "source_percentile_tone_anchors": [0.01, 0.99], "learned_tone": "reference within-image quantile shape, scaled to the source 1st/99th percentile span", "color_identity_prior": 0.20, "transport_eigenvalue_range": [0.55, 1.45], "ab_offset_limit_before_prior": 18, "creative_chroma_floor_ratio": mapping["creative_chroma_floor_ratio"], "endpoint_chroma_fade": True, "gamut": "reduce Lab chroma toward neutral at fixed fitted L*, then encode sRGB"},
        "reference_weighting": "All corpus images receive one vote for source-compatible mode selection; the selected creative mode uses componentwise medians, with no pixel-count weighting across photographs.",
        "sampling": {"maximum_edge": MAX_EDGE, "maximum_pixels_per_image": MAX_SAMPLES, "luma_bins": LUMA_BINS, "jpeg_reduced_decode_factor": 4},
        "qc": qc, "warnings": warnings, "manifest_path": str(manifest_path),
        "lut_path": str(cube_path), "lut_sha256": hashlib.sha256(cube_path.read_bytes()).hexdigest(),
    }
    _atomic_write_string(profile_path, json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
    return {
        "status": "success", "method": METHOD, "source_dependent": True,
        "style_name": style_name, "reference_count": counts["accepted"], "counts": counts,
        "selected_reference_count": target["selection"]["selected_count"],
        "color_image_ratio": target["color_image_ratio"], "strength": float(strength),
        "lut_path": str(cube_path), "profile_path": str(profile_path), "manifest_path": str(manifest_path),
        "lut_sha256": profile["lut_sha256"], "qc": qc, "warnings": warnings,
    }
