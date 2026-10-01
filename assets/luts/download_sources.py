"""Reproduce the selected public LUT downloads without executing upstream code.

Run explicitly with network access. Files are pinned to commits and kept verbatim.
Use catalog.json checksums to verify the downloaded copies afterward.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib

ROOT = Path(__file__).resolve().parent
PATRON_COMMIT = "af7b50d4caf6244fb6895a647f5b6a84efe7931a"
LUMIX_COMMIT = "708f98d97a26b123128480050c2a1459c8a58cca"
PATRON_BASE = f"https://raw.githubusercontent.com/NatronGitHub/clut/{PATRON_COMMIT}/"
LUMIX_BASE = f"https://raw.githubusercontent.com/t0saki/lumix-original-looks/{LUMIX_COMMIT}/"
SOURCES = [
    (PATRON_BASE + "README.md", "pat-david-cc-by-sa-4.0/UPSTREAM_README.md"),
    (PATRON_BASE + "negative_new/kodak_portra_160.png", "pat-david-cc-by-sa-4.0/originals/kodak_portra_160.png"),
    (PATRON_BASE + "negative_new/kodak_portra_400.png", "pat-david-cc-by-sa-4.0/originals/kodak_portra_400.png"),
    (PATRON_BASE + "colorslide/fuji_provia_100f.png", "pat-david-cc-by-sa-4.0/originals/fuji_provia_100f.png"),
    (PATRON_BASE + "colorslide/fuji_velvia_50.png", "pat-david-cc-by-sa-4.0/originals/fuji_velvia_50.png"),
    (PATRON_BASE + "negative_old/fuji_superia_800.png", "pat-david-cc-by-sa-4.0/originals/fuji_superia_800.png"),
    (PATRON_BASE + "bw/kodak_tri-x_400.png", "pat-david-cc-by-sa-4.0/originals/kodak_tri-x_400.png"),
    ("https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt", "pat-david-cc-by-sa-4.0/LICENSE-CC-BY-SA-4.0.txt"),
    (LUMIX_BASE + "LICENSE", "lumix-original-mit/LICENSE"),
    (LUMIX_BASE + "README.md", "lumix-original-mit/UPSTREAM_README.md"),
    (LUMIX_BASE + "luts/manifest.json", "lumix-original-mit/UPSTREAM_MANIFEST.json"),
    (LUMIX_BASE + "luts/Meridian.cube", "lumix-original-mit/Meridian.cube"),
    (LUMIX_BASE + "luts/Lowsun.cube", "lumix-original-mit/Lowsun.cube"),
]


def download(item):
    url, relative = item
    destination = ROOT / relative
    request = Request(url, headers={"User-Agent": "AI-Colorist-LUT-audit"})
    with urlopen(request, timeout=45) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError(f"Unexpectedly large source: {url}")
    if destination.suffix == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Source is not a PNG: {url}")
    if destination.suffix == ".cube" and b"LUT_3D_SIZE" not in data:
        raise ValueError(f"Source is not a 3D CUBE: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return f"{relative}: {len(data)} bytes sha256={hashlib.sha256(data).hexdigest()}"


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(download, SOURCES):
            print(result, flush=True)
