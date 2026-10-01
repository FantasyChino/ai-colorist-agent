"""Read standard red-fastest 3D .cube LUTs and apply continuous interpolation."""

from pathlib import Path

import numpy as np


def load_cube(path):
    """Load a 3D cube, checking its dimensions, numeric data, and input domain."""
    rows = []
    size = None
    domain_min = np.zeros(3, dtype=np.float32)
    domain_max = np.ones(3, dtype=np.float32)
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.partition("#")[0].strip()
            if not line:
                continue
            tokens = line.split()
            keyword = tokens[0]
            try:
                if keyword == "TITLE":
                    continue
                if keyword == "LUT_1D_SIZE":
                    raise ValueError("1D or combined shaper LUTs are not supported")
                if keyword == "LUT_3D_SIZE":
                    if size is not None or len(tokens) != 2:
                        raise ValueError("Invalid or duplicate LUT_3D_SIZE")
                    size = int(tokens[1])
                elif keyword in ("DOMAIN_MIN", "DOMAIN_MAX"):
                    if len(tokens) != 4:
                        raise ValueError("Input domain requires three numbers")
                    values = np.array(tokens[1:], dtype=np.float32)
                    if keyword == "DOMAIN_MIN":
                        domain_min = values
                    else:
                        domain_max = values
                else:
                    if len(tokens) != 3:
                        raise ValueError("Expected an RGB table row")
                    rows.append([float(value) for value in tokens])
            except ValueError as exc:
                raise ValueError(f"Invalid cube at line {line_number}: {exc}") from exc

    if size is None or not 2 <= size <= 256:
        raise ValueError("LUT_3D_SIZE must be between 2 and 256")
    table = np.asarray(rows, dtype=np.float32)
    if table.shape != (size ** 3, 3) or not np.all(np.isfinite(table)):
        raise ValueError(f"Cube must contain exactly {size ** 3} finite RGB rows")
    if not np.all(np.isfinite([domain_min, domain_max])) or np.any(domain_max <= domain_min):
        raise ValueError("Cube input domain must be finite and increasing")
    return {"size": size, "table": table, "domain_min": domain_min, "domain_max": domain_max}


def apply_simple_lut(image, lut):
    """Apply a 3D LUT to an 8-bit BGR image, with bounded-memory trilinear sampling.

    Cube rows vary red fastest, then green, then blue. Interpolation preserves
    intermediate values: even a two-point identity cube must preserve a ramp.
    This does not perform ICC, log, RAW, or gamut conversion.
    """
    size = lut["size"]
    table = np.asarray(lut["table"], dtype=np.float32)
    if not isinstance(size, (int, np.integer)) or not 2 <= size <= 256:
        raise ValueError("Invalid LUT size")
    if table.shape != (size ** 3, 3) or not np.all(np.isfinite(table)):
        raise ValueError("Invalid LUT table")
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("LUT input must be an 8-bit BGR image")
    domain_min = np.asarray(lut.get("domain_min", [0, 0, 0]), dtype=np.float32)
    domain_max = np.asarray(lut.get("domain_max", [1, 1, 1]), dtype=np.float32)
    if (
        domain_min.shape != (3,) or domain_max.shape != (3,)
        or not np.all(np.isfinite([domain_min, domain_max]))
        or np.any(domain_max <= domain_min)
    ):
        raise ValueError("Invalid LUT input domain")

    # C-order shape indexes are blue, green, red because red varies fastest.
    grid = table.reshape(size, size, size, 3)
    source = image.reshape(-1, 3)
    output = np.empty_like(source)
    for start in range(0, len(source), 65536):
        stop = min(start + 65536, len(source))
        rgb = source[start:stop, ::-1].astype(np.float32) / 255.0
        coordinates = np.clip((rgb - domain_min) / (domain_max - domain_min), 0, 1) * (size - 1)
        lower = np.floor(coordinates).astype(np.int32)
        upper = np.minimum(lower + 1, size - 1)
        fraction = coordinates - lower
        result = np.zeros_like(rgb)
        for blue in (0, 1):
            for green in (0, 1):
                for red in (0, 1):
                    r = upper[:, 0] if red else lower[:, 0]
                    g = upper[:, 1] if green else lower[:, 1]
                    b = upper[:, 2] if blue else lower[:, 2]
                    weight = (
                        (fraction[:, 0] if red else 1 - fraction[:, 0])
                        * (fraction[:, 1] if green else 1 - fraction[:, 1])
                        * (fraction[:, 2] if blue else 1 - fraction[:, 2])
                    )
                    result += grid[b, g, r] * weight[:, None]
        output[start:stop] = np.rint(np.clip(result[:, ::-1] * 255, 0, 255)).astype(np.uint8)
    return output.reshape(image.shape)

