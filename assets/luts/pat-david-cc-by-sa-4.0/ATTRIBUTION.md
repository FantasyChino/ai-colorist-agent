# Pat David film-emulation LUTs

Original creative film-emulation approximations by **Pat David**.

- Author: <https://patdavid.net/>
- Original explanation: <https://patdavid.net/2013/08/film-emulation-presets-in-gmic-gimp/>
- Original author's RawTherapee integration: <https://patdavid.net/2015/03/film-emulation-in-rawtherapee/>
- Download source: <https://github.com/NatronGitHub/clut>
- Fixed source commit: `af7b50d4caf6244fb6895a647f5b6a84efe7931a`
- License: **Creative Commons Attribution-ShareAlike 4.0 International (CC-BY-SA-4.0)**.
- License URL: <https://creativecommons.org/licenses/by-sa/4.0/>
- Full license text: `LICENSE-CC-BY-SA-4.0.txt`.
- Repository notice retained verbatim: `UPSTREAM_README.md`.

Selected original 16-bit RGB Hald PNGs are retained verbatim in `originals/`:

| Filename | Upstream directory |
| --- | --- |
| kodak_portra_160.png | negative_new |
| kodak_portra_400.png | negative_new |
| fuji_provia_100f.png | colorslide |
| fuji_velvia_50.png | colorslide |
| fuji_superia_800.png | negative_old |
| kodak_tri-x_400.png | bw |

On 2026-10-01, AI Colorist converted these Hald assets to corresponding `.cube`
tables, resampling the original 64-point RGB lattice to a 33-point lattice using
trilinear interpolation. The CUBE tables use RGB triplets with red changing
fastest, an explicit unit input domain, and nine decimal places. No creative
look adjustments, gamma conversion, ICC conversion, or photo editing were added.
The conversion script and numerical comparison are in `../prepare_library.py`
and `../catalog.json`. This resampling is an approximation, not an exact copy
of every original 64-point value; the originals remain available for higher
precision conversions.

All original assets and converted tables in this directory retain CC-BY-SA-4.0.
Keep this attribution, the source links, license, and modification notice when
redistributing these LUTs or further adapted LUT assets. Their license does not
relicense unrelated project code. Consult the retained full license for its
conditions and disclaimer; no warranty or creator endorsement is asserted.

Film names identify the author's approximate creative target. They do not
certify measurements of actual stock, and neither the original creators nor
this project are affiliated with or endorsed by the trademark owners.

Input/output sRGB is a **collection-family assumption** supported by the related
RawTherapee film-emulation documentation. These exact Natron PNGs have no sRGB,
gamma, or ICC metadata, and Natron's README gives no per-file color encoding.
The catalog records that uncertainty. Validate each candidate visually on the
actual display-referred JPEG; do not feed camera Log, linear light, HDR, P3, or
AdobeRGB values to it under this assumption.
